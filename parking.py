from flask import Flask, Response, request, send_from_directory, jsonify
from flask_cors import CORS
import pandas as pd
from sklearn.cluster import DBSCAN
import datetime
import io
import os
import re
import requests
from dotenv import load_dotenv

import parking_maps
import parking_zones

load_dotenv()

app = Flask(__name__, static_folder="frontend/my-app/build", static_url_path="")
CORS(app, origins=["http://localhost:3000"])

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


# Street suffixes, long form -> the abbreviation SFMTA actually stores, so that
# "geary boulevard" and "GEARY BLVD" normalize to the same thing.
STREET_SUFFIXES = {
    "street": "st", "avenue": "ave", "boulevard": "blvd", "road": "rd",
    "drive": "dr", "terrace": "ter", "place": "pl", "court": "ct",
    "lane": "ln", "parkway": "pkwy", "highway": "hwy", "circle": "cir",
    "square": "sq", "alley": "aly",
}
SUFFIX_RE = re.compile(r'\b(' + '|'.join(STREET_SUFFIXES) + r')\b')


def normalize_addr(addr):
    addr = str(addr).lower().replace(".", "")
    addr = SUFFIX_RE.sub(lambda m: STREET_SUFFIXES[m.group(1)], addr)
    return re.sub(r'[^a-z0-9 ]', '', addr).strip()


# ============================================
# LOAD DATA
# ============================================

# Live SFMTA citations: https://data.sf.gov/Transportation/SFMTA-Parking-Citations-Fines/ab4h-6ztd
SODA_URL = "https://data.sf.gov/resource/ab4h-6ztd.csv"
CACHE_PATH = "data/citations_cache.csv"
USF_CAMPUS = (37.7763, -122.4505)
DAYS_BACK = int(os.getenv("CITATION_DAYS", 90))
RADIUS_M = int(os.getenv("CITATION_RADIUS_M", 1500))
PAGE_SIZE = 50000


def fetch_citations():
    """Page through the SODA API for recent citations near campus."""
    since = (datetime.datetime.now() - datetime.timedelta(days=DAYS_BACK)).strftime("%Y-%m-%dT%H:%M:%S")
    headers = {"X-App-Token": os.environ["SODA_APP_TOKEN"]} if os.getenv("SODA_APP_TOKEN") else {}
    params = {
        "$select": "citation_number, citation_issued_datetime AS issue_datetime, citation_location AS address, violation_desc, fine_amount, latitude, longitude",
        "$where": f"citation_issued_datetime > '{since}' AND within_circle(the_geom, {USF_CAMPUS[0]}, {USF_CAMPUS[1]}, {RADIUS_M})",
        "$order": "citation_number",
        "$limit": PAGE_SIZE,
    }
    pages = []
    while True:
        resp = requests.get(SODA_URL, params={**params, "$offset": PAGE_SIZE * len(pages)}, headers=headers, timeout=60)
        resp.raise_for_status()
        page = pd.read_csv(io.StringIO(resp.text))
        pages.append(page)
        if len(page) < PAGE_SIZE:
            return pd.concat(pages, ignore_index=True)


def load_citations():
    """Fetch live data and refresh the cache; fall back to the cache if the API is unreachable."""
    try:
        data = fetch_citations()
        data.to_csv(CACHE_PATH, index=False)
        print(f"✓ Fetched {len(data)} citations from DataSF (last {DAYS_BACK} days)")
        return data
    except (requests.RequestException, pd.errors.ParserError) as e:
        if not os.path.exists(CACHE_PATH):
            raise RuntimeError(f"DataSF fetch failed and no cache at {CACHE_PATH}") from e
        print(f"WARNING: DataSF fetch failed ({e}); using cached {CACHE_PATH}")
        return pd.read_csv(CACHE_PATH)


df = load_citations()
df['issue_datetime'] = pd.to_datetime(df['issue_datetime'])
df = df.dropna(subset=["latitude", "longitude"]).sort_values('issue_datetime')

if 'address' in df.columns:
    df['address_normalized'] = df['address'].apply(normalize_addr)
    print(f"✓ Loaded {len(df)} citations with addresses")
else:
    print("WARNING: 'address' column not found in CSV!")

# ============================================
# CREATE ZONES USING DBSCAN
# ============================================

# eps ≈ 55 m; min_samples scales with row count so a longer CITATION_DAYS window doesn't merge all zones into one
min_samples = max(10, len(df) // 600)
df["zone_id"] = DBSCAN(eps=0.0005, min_samples=min_samples).fit(df[["latitude", "longitude"]].to_numpy()).labels_
df["hour"] = df["issue_datetime"].dt.hour
df["dayofweek"] = df["issue_datetime"].dt.dayofweek

# ============================================
# ZONE STATISTICS
# ============================================

total_days = max(1, (df['issue_datetime'].max() - df['issue_datetime'].min()).days)

zoned = df[df["zone_id"] != -1].groupby("zone_id")
zone_stats = zoned.agg(
    total_tickets=('zone_id', 'count'),
    peak_hour=('hour', lambda x: x.mode()[0] if len(x) > 0 else 12),
    peak_day=('dayofweek', lambda x: x.mode()[0] if len(x) > 0 else 2),
).join(zoned[["latitude", "longitude"]].mean())
zone_stats['tickets_per_day'] = zone_stats['total_tickets'] / total_days
max_tickets = zone_stats['tickets_per_day'].max()
zone_stats['base_risk_score'] = (zone_stats['tickets_per_day'] / max_tickets * 100).round(1) if max_tickets > 0 else 0

print(f"✓ Risk scoring computed for {len(zone_stats)} zones")
print(f"✓ Data period: {total_days} days")

# ============================================
# STREET INDEX (risk-check autocomplete)
# ============================================

# Addresses arrive as "1247 FULTON ST"; drop the house number to get the street.
HOUSE_NUMBER = re.compile(r'^\d+[A-Z]?\s+')


def build_street_index():
    """Distinct street names from the citations, most-ticketed first.

    Derived from the same address column /zone-info matches against, so every
    suggestion the frontend offers is guaranteed to resolve.
    """
    if 'address' not in df.columns:
        return []
    streets = (df['address'].dropna().astype(str).str.strip().str.upper()
               .str.replace(HOUSE_NUMBER, '', regex=True).str.strip())
    streets = streets[streets.str.len() > 2]
    return [{'name': name, 'citations': int(count)}
            for name, count in streets.value_counts().items()]


street_index = build_street_index()
street_norms = [normalize_addr(s['name']) for s in street_index]
print(f"✓ Street index built for {len(street_index)} streets")

# ============================================
# HELPERS
# ============================================

def categorize_risk(score):
    if score < 10:
        return "Low", "#00FF00", "✅ Safe to park here"
    elif score < 40:
        return "Medium", "#FFA500", "⚠️ Park with caution"
    return "High", "#FF0000", "🚨 Avoid parking here"


def zone_risk(zone_id, now):
    """Risk details for a zone, with the base score boosted during its peak hour/day."""
    stats = zone_stats.loc[zone_id]
    is_peak_hour = abs(now.hour - stats['peak_hour']) <= 1
    is_peak_day = now.weekday() == stats['peak_day']

    score = float(stats['base_risk_score'])
    if is_peak_hour and is_peak_day:
        score *= 1.5
    elif is_peak_hour or is_peak_day:
        score *= 1.2
    score = min(100, score)

    risk_level, risk_color, recommendation = categorize_risk(score)
    return {
        'zone_id': int(zone_id),
        'risk_score': round(score, 1),
        'risk_level': risk_level,
        'risk_color': risk_color,
        'recommendation': recommendation,
        'is_peak_time': bool(is_peak_hour and is_peak_day),
        'peak_info': {'hour': int(stats['peak_hour']), 'day': DAYS[int(stats['peak_day'])]},
        'statistics': {
            'total_tickets': int(stats['total_tickets']),
            'tickets_per_day': round(float(stats['tickets_per_day']), 2),
            'data_period_days': total_days
        },
        'location': {'latitude': float(stats['latitude']), 'longitude': float(stats['longitude'])},
        'timestamp': now.isoformat(),
    }


def ranked_zones(key, reverse):
    now = datetime.datetime.now()
    zones_list = []
    for zone_id in zone_stats.index:
        r = zone_risk(zone_id, now)
        zones_list.append({
            'zone_id': r['zone_id'],
            'risk_score': r['risk_score'],
            'risk_level': r['risk_level'],
            **r['location'],
        })
    zones_list.sort(key=lambda z: z['risk_score'], reverse=reverse)
    return jsonify({'timestamp': now.isoformat(), key: zones_list[:5]})

# ============================================
# FLASK ENDPOINTS
# ============================================

@app.route('/risk-score/<int:zone_id>')
def get_zone_risk_score(zone_id):
    if zone_id not in zone_stats.index:
        return jsonify({'error': 'Zone not found'}), 404
    return jsonify(zone_risk(zone_id, datetime.datetime.now()))


@app.route('/safest-zones')
def get_safest_zones():
    return ranked_zones('safest_zones', reverse=False)


@app.route('/danger-zones')
def get_danger_zones():
    return ranked_zones('danger_zones', reverse=True)


@app.route('/maps/street-hours')
@app.route('/maps/combined')
@app.route('/maps/heatmap')
def get_live_map():
    """Render a time-dependent map for the current hour.

    These two views colour streets by the parking limit in force right now, so
    they are built on request instead of being served as pre-rendered files.
    parking_maps caches the HTML per hour, which is as often as the colours can
    change.
    """
    name = request.path.rsplit('/', 1)[-1]
    html, stats = parking_maps.render(name)
    # Let the browser reuse it until the top of the next hour, when colours may change.
    now = datetime.datetime.now()
    seconds_left = 3600 - (now.minute * 60 + now.second)
    headers = {
        'Cache-Control': f'public, max-age={seconds_left}',
        'X-Map-Generated': stats['generated'].isoformat(timespec='seconds'),
    }
    # Only report the counts this particular map actually has.
    for field, header in (('zones', 'X-Map-Zones'), ('citations_this_hour', 'X-Map-Citations')):
        if field in stats:
            headers[header] = str(stats[field])
    return Response(html, mimetype='text/html', headers=headers)


@app.route('/streets')
def get_streets():
    """Street names for the risk-check autocomplete, most-ticketed first.

    The whole list is a few hundred entries, so the frontend fetches it once and
    filters as the user types. `q` narrows it server-side for anyone who wants to.
    """
    query = request.args.get('q', '').strip()
    try:
        limit = max(1, min(500, int(request.args.get('limit', 500))))
    except ValueError:
        limit = 500

    if query:
        needle = normalize_addr(query)
        matches = [street for street, norm in zip(street_index, street_norms) if needle in norm]
    else:
        matches = street_index

    return jsonify({'total': len(matches), 'streets': matches[:limit]})


@app.route('/zones')
def get_zones():
    """Parking regulations near campus as GeoJSON; drives the street-parking maps."""
    return jsonify(parking_zones.load_zones())


@app.route('/zone-info/<path:street_name>')
def zone_info(street_name):
    if 'address' not in df.columns:
        return jsonify({'error': 'Address column not found in dataset'}), 500

    matches = df[df['address_normalized'].str.contains(normalize_addr(street_name), na=False, regex=False)]
    if matches.empty:
        return jsonify({
            'error': f'Street "{street_name}" not found in dataset',
            'suggestion': 'Try a different street name or check spelling'
        }), 404

    zone_id = int(matches.iloc[0]['zone_id'])

    # Noise points (zone_id = -1) aren't part of any high-citation zone
    if zone_id == -1:
        return jsonify({
            'error': 'This street is not in a high-citation zone',
            'zone_id': -1,
            'risk_level': 'Low',
            'risk_color': '#00FF00',
            'recommendation': '✅ This area has very few citations',
            'total_tickets': len(matches),
            'message': 'Not enough citation data to create a risk zone here'
        }), 200

    if zone_id not in zone_stats.index:
        return jsonify({'error': 'Zone statistics not available'}), 404

    return jsonify({**zone_risk(zone_id, datetime.datetime.now()), 'matched_address': matches.iloc[0]['address']})

# ============================================
# Serve React
# ============================================

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
