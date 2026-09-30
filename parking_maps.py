"""Folium map builders for the street-parking views.

The colours on these maps depend on the time of day, so they are built on demand
(see the /maps/* routes in parking.py) rather than shipped as pre-rendered files.
Rendered HTML is cached per hour, which is as fine-grained as the SFMTA
regulation windows get.

scripts/create_line_map.py and scripts/create_combined_map.py call the same
builders to write static copies into the React public folder.
"""

import os
from datetime import datetime
from functools import lru_cache
from math import atan2, cos, radians, sin, sqrt

import folium
import folium.plugins
import pandas as pd
from folium.plugins import HeatMap
from sklearn.cluster import DBSCAN

import parking_zones

ROOT = os.path.dirname(os.path.abspath(__file__))
CITATIONS_PATH = os.path.join(ROOT, "data", "citations_cache.csv")
PUBLIC_MAPS_DIR = os.path.join(ROOT, "frontend", "my-app", "public", "maps")

USF_CENTER = [37.7765, -122.4505]

NO_PARKING_RULES = ("NO PARKING", "TOW-AWAY", "NO STOPPING")

HEATMAP_RADIUS_MILES = 1.0
MIN_CLUSTER_SIZE = 15
MIN_SAMPLES = 10
# Citations are bucketed by hour of day; +/-1 hour keeps the sample usable while
# still describing "right now" rather than the whole 90-day window.
HOUR_WINDOW = 1

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
# The live feed is far denser than the CSV this map was first built from, so cap
# the markers to the biggest hotspots; 385 of them would bury the street colours.
MAX_CLUSTER_MARKERS = 25

LEGEND_ROWS = [
    ("#FF0000", "No Parking Now"),
    ("#FFFF00", "1 Hour Limit"),
    ("#FFA500", "2 Hour Limit"),
    ("#00FF00", "3+ Hours / Unrestricted"),
]

# SFMTA abbreviates violation descriptions; spell them out for the popups. Codes
# not listed here fall through to the raw abbreviation rather than being dropped.
VIOLATION_NAMES = {
    'STR CLEAN': 'Street cleaning',
    'MTR OUT DT': 'Expired meter',
    'RES/OT': 'Residential permit overtime',
    'PRK GRADE': 'Parked on a grade (wheels not curbed)',
    'RED ZONE': 'Parked in a red zone',
    'DRIVEWAY': 'Blocking a driveway',
    'NO PLATES': 'Missing licence plates',
    'OT OUT DT': 'Overtime parking',
    'FAIL DISPL': 'Failure to display permit',
    'YEL ZONE': 'Parked in a yellow loading zone',
    'ON SIDEWLK': 'Parked on the sidewalk',
    'PK STANDS': 'Parked in a taxi stand',
    'DBL PARK': 'Double parked',
    'TRK ZONE': 'Parked in a truck loading zone',
    'PK PHB OTD': 'Parking prohibited',
    '20FT XWALK': 'Within 20 ft of a crosswalk',
    'OBSTRCT TF': 'Obstructing traffic',
    'CNSTR TEMP': 'Temporary construction restriction',
    'WHITE ZONE': 'Parked in a white passenger zone',
    'NO EV REG': 'Unregistered vehicle in EV space',
    'BUS ZONE': 'Parked in a bus zone',
    'FIRE HYD': 'Parked by a fire hydrant',
    'OVR 18 " C': 'More than 18 inches from the curb',
    'OVR 18 \\" C': 'More than 18 inches from the curb',
    'TMP PK RES': 'Temporary parking restriction',
    'PLT LEF/AT': 'Plate not properly attached',
    'PK/CROSS': 'Parked in a crosswalk',
    'WHLCHR ACC': 'Blocking wheelchair access',
    'FAILRPLPLA': 'Failure to replace plate',
    'ANGLE PARK': 'Improper angle parking',
    'BLK BIKE L': 'Blocking a bike lane',
    'N/ W/I SPC': 'Not within a marked space',
    'PK OVR 72H': 'Parked over 72 hours',
    'DISOB SIGN': 'Disobeying a posted sign',
    'PLATECOVER': 'Illegal plate cover',
    'NO VIOL': 'No violation',
    'B ZN NO DP': 'Blue zone without a placard',
    'ONSTCARSH': 'On-street car share space',
    'NO PRK ZN': 'Parked in a no-parking zone',
    'NOPRK 10P6': 'No parking 10pm-6am',
    'OT MTR PK': 'Overtime at a meter',
    'GREEN ZONE': 'Parked in a green short-term zone',
    'RESTRICTED': 'Restricted area',
    'LARGE VEHI': 'Oversized vehicle',
    'MC PRKING': 'Motorcycle parking violation',
    'ILL PKG': 'Illegal parking',
    '3 FT WLCHR': 'Within 3 ft of a wheelchair ramp',
    'ONEWAY RD': 'Wrong side of a one-way street',
    'PK INTER': 'Parked in an intersection',
    'REG TABS': 'Expired registration tabs',
    'SMOKNG ETC': 'Smoking violation',
    'RR TRACKS': 'Parked on railroad tracks',
    'B ZN XHTCH': 'Blue zone crosshatch area',
    'CM VEH RES': 'Commercial vehicle restriction',
    'MED DIVIDE': 'Parked on a median',
    'WRG WY PKG': 'Parked facing the wrong way',
    'NOPL/PRDSP': 'No plate or improper display',
    'NO PERMIT': 'No permit displayed',
    'PRK PROHIB': 'Parking prohibited',
    'PKG PROHIB': 'Parking prohibited',
    'METER DTN': 'Expired meter (downtown)',
    'SAFE/RED Z': 'Stopped in a no-stopping zone',
}

# ============================================
# REGULATION LOGIC
# ============================================


def get_max_hours(props):
    """Hour limit for a regulation, or None when it is unrestricted/unknown."""
    if props.get("max_hours") is not None:
        return props["max_hours"]

    begin, end = props.get("hrs_begin"), props.get("hrs_end")
    if begin and end:
        try:
            begin, end = int(begin), int(end)
            duration = (end // 100 + end % 100 / 60) - (begin // 100 + begin % 100 / 60)
            if duration > 0:
                return duration
        except (TypeError, ValueError):
            pass

    rule = str(props.get("regulation") or "").upper()
    if any(x in rule for x in NO_PARKING_RULES):
        return 0
    for hours in (1, 2, 3, 4):
        if any(f"{hours} {unit}" in rule or f"{hours}{unit}" in rule for unit in ("HR", "HOUR")):
            return hours
    return None


def is_parking_allowed_now(props, check_time):
    """(allowed, hour_limit) for a regulation at `check_time`.

    A regulation only binds on the days and during the hours it lists; outside
    those the block is unrestricted, which is reported as (True, None).
    """
    weekday = check_time.weekday()
    day_name = ["M", "TU", "W", "TH", "F", "SA", "SU"][weekday]
    now_hhmm = check_time.hour * 100 + check_time.minute

    days = str(props.get("days") or "").upper()
    regulation = str(props.get("regulation") or "").upper()
    begin, end = props.get("hrs_begin"), props.get("hrs_end")

    if days:
        if "M-SU" in days or "DAILY" in days:
            pass  # in force every day
        elif "M-F" in days:
            if weekday >= 5:
                return True, None
        elif "M-SA" in days:
            if weekday == 6:
                return True, None
        elif "SA-SU" in days or days in ("SA", "SU"):
            if weekday < 5:
                return True, None
        elif day_name not in days:
            return True, None

    if begin and end:
        try:
            begin_hhmm, end_hhmm = int(begin), int(end)
        except (TypeError, ValueError):
            begin_hhmm = end_hhmm = None
        if begin_hhmm is not None:
            # A window like 2400-600 wraps past midnight, so it is active when the
            # time is after the start OR before the end, not between the two.
            if begin_hhmm > end_hhmm:
                in_window = now_hhmm >= begin_hhmm or now_hhmm <= end_hhmm
            else:
                in_window = begin_hhmm <= now_hhmm <= end_hhmm
            if not in_window:
                return True, None

    if any(x in regulation for x in NO_PARKING_RULES):
        return False, 0
    return True, get_max_hours(props)


def get_color_by_availability(is_allowed, hours):
    if not is_allowed or (hours is not None and hours <= 0):
        return "#FF0000"
    if hours is None:
        return "#00FF00"
    if hours == 1:
        return "#FFFF00"
    if hours == 2:
        return "#FFA500"
    return "#00FF00"


def to_latlon_lines(geom):
    """GeoJSON (lon, lat) geometry -> list of folium (lat, lon) polylines."""
    if geom["type"] == "LineString":
        lines = [geom["coordinates"]]
    elif geom["type"] == "MultiLineString":
        lines = geom["coordinates"]
    else:
        return []
    return [[[lat, lon] for lon, lat in line] for line in lines if len(line) >= 2]


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles between two lat/lon points."""
    radius = 3959
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return radius * 2 * atan2(sqrt(a), sqrt(1 - a))

# ============================================
# CACHED INPUTS
# ============================================

# Parsing the regulations and clustering the citations is the slow part and does
# not depend on the time, so both are cached. The file mtime is part of the key
# so a refreshed file is picked up without a restart.


@lru_cache(maxsize=1)
def _zone_features(_mtime):
    return parking_zones.load_zones()["features"]


def zone_features():
    try:
        mtime = os.path.getmtime(parking_zones.REGULATIONS_PATH)
    except OSError:
        mtime = None
    return _zone_features(mtime)


@lru_cache(maxsize=1)
def _citations(_mtime):
    """Citations near campus with hour/weekday columns, or None if unavailable.

    Hour-independent, so it is cached and reused across renders; the per-hour
    filtering happens in the builders.
    """
    if not os.path.exists(CITATIONS_PATH):
        return None

    df = pd.read_csv(CITATIONS_PATH)
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[(df["latitude"] != 0) & (df["longitude"] != 0)]

    df["distance_miles"] = [
        haversine_miles(USF_CENTER[0], USF_CENTER[1], lat, lon)
        for lat, lon in zip(df["latitude"], df["longitude"])
    ]
    df = df[df["distance_miles"] <= HEATMAP_RADIUS_MILES]
    if df.empty:
        return None

    issued = pd.to_datetime(df["issue_datetime"], errors="coerce")
    df = df.assign(hour=issued.dt.hour, weekday=issued.dt.dayofweek)
    df = df.dropna(subset=["hour", "weekday"])

    if "violation_desc" in df.columns:
        df["violation_desc"] = (
            df["violation_desc"].astype(str).str.strip().replace(VIOLATION_NAMES)
        )
    return df.reset_index(drop=True)


def citations():
    """The citation frame, reloaded when the cache file changes."""
    try:
        mtime = os.path.getmtime(CITATIONS_PATH)
    except OSError:
        mtime = None
    return _citations(mtime)


def _hours_from(hours, hour):
    """Circular distance in hours, so 23:00 is one hour from midnight."""
    gap = (hours - hour).abs()
    return gap.where(gap <= 12, 24 - gap)


def this_hour(df, check_time, same_weekday=False):
    """Citations issued within HOUR_WINDOW hours of check_time's hour."""
    mask = _hours_from(df["hour"], check_time.hour) <= HOUR_WINDOW
    if same_weekday:
        mask &= df["weekday"] == check_time.weekday()
    return df[mask]


def find_clusters(df, max_markers=MAX_CLUSTER_MARKERS):
    """(clusters, total_significant) for the densest citation clusters in `df`.

    Each cluster carries what the popup shows: how many tickets, the main reasons
    with their share, typical fine, when it peaks and the most-cited addresses.
    """
    if len(df) < MIN_SAMPLES:
        return [], 0

    labels = DBSCAN(eps=0.0002, min_samples=MIN_SAMPLES).fit(
        df[["latitude", "longitude"]].to_numpy()
    ).labels_
    df = df.assign(cluster=labels)

    sizes = df[df["cluster"] != -1].groupby("cluster").size()
    significant = sizes[sizes >= MIN_CLUSTER_SIZE].sort_values(ascending=False)
    total = len(significant)
    layer_total = len(df)

    clusters = []
    for cluster_id, count in significant.head(max_markers).items():
        rows = df[df["cluster"] == cluster_id]
        count = int(count)

        reasons = []
        if "violation_desc" in rows:
            for name, n in rows["violation_desc"].value_counts().head(4).items():
                reasons.append((str(name), int(n), round(n / count * 100)))

        fines = rows["fine_amount"].dropna() if "fine_amount" in rows else []
        addresses = [
            (str(a), int(n)) for a, n in rows["address"].value_counts().head(3).items()
        ] if "address" in rows else []

        clusters.append({
            "count": count,
            "lat": float(rows["latitude"].mean()),
            "lon": float(rows["longitude"].mean()),
            "share": round(count / layer_total * 100, 1) if layer_total else 0,
            "reasons": reasons,
            "fine_typical": float(fines.median()) if len(fines) else None,
            "fine_total": float(fines.sum()) if len(fines) else None,
            "peak_hour": int(rows["hour"].mode()[0]) if "hour" in rows and len(rows) else None,
            "peak_day": DAY_NAMES[int(rows["weekday"].mode()[0])] if "weekday" in rows and len(rows) else None,
            "addresses": addresses,
        })
    return clusters, total


def heat_layer(df, name, show):
    """A toggleable heatmap layer over the rows of `df`."""
    layer = folium.FeatureGroup(name=f"{name} ({len(df)})", show=show)
    HeatMap(
        df[["latitude", "longitude"]].values.tolist(),
        radius=10,
        blur=5,
        max_zoom=1,
        min_opacity=0.3,
        gradient={0.0: "rgba(0,0,255,0)", 0.3: "green", 0.6: "yellow", 1.0: "red"},
    ).add_to(layer)
    return layer


def cluster_marker_layer(clusters, name, show):
    """A toggleable layer of markers on the densest clusters."""
    layer = folium.FeatureGroup(name=f"{name} ({len(clusters)})", show=show)
    for cluster in clusters:
        folium.CircleMarker(
            location=[cluster["lat"], cluster["lon"]],
            radius=6,
            color="red",
            fill=True,
            fillColor="red",
            fillOpacity=0.7,
            popup=folium.Popup(cluster_popup_html(cluster), max_width=300),
            tooltip=f"Cluster: {cluster['count']} citations (click for details)",
        ).add_to(layer)
    return layer


# ============================================
# HTML FRAGMENTS
# ============================================

GEOCODER_CSS = """
<style>
.leaflet-bottom.leaflet-left {
    left: 50% !important;
    transform: translateX(-50%) !important;
    bottom: 30px !important;
    z-index: 1000 !important;
    width: 70% !important;
    max-width: 900px !important;
}
.leaflet-control-geocoder {
    background: rgba(0, 77, 64, 0.55) !important;
    backdrop-filter: blur(15px) !important;
    border-radius: 2.5rem !important;
    padding: 10px 18px !important;
    width: 100% !important;
    height: 60px !important;
    display: flex !important;
    align-items: center !important;
}
.leaflet-control-geocoder-form { width: 100% !important; display: flex !important; gap: 10px !important; }
.leaflet-control-geocoder-form input {
    flex: 1 !important;
    background: rgba(255, 255, 255, 0.25) !important;
    border-radius: 1.5rem !important;
    padding: 10px 14px !important;
    font-size: 1.1rem !important;
    color: #f1f1f1 !important;
    border: none !important;
    outline: none !important;
}
.leaflet-control-geocoder-form input::placeholder { color: rgba(255, 255, 255, 0.85) !important; }
.leaflet-control-geocoder-icon { display: none !important; }
.leaflet-control-geocoder-alternatives {
    max-height: 150px !important;
    overflow-y: auto !important;
    background: rgba(0, 77, 64, 0.85) !important;
    border-radius: 1rem !important;
}
.leaflet-control-geocoder-alternatives li { color: #fff !important; padding: 8px 14px !important; }
.leaflet-control-geocoder-alternatives li:hover { background: rgba(76, 175, 80, 0.25) !important; }
</style>
"""


def _legend_rows_html():
    return "".join(
        f'<div style="display: flex; align-items: center; margin-bottom: 5px;">'
        f'<div style="width: 18px; height: 18px; background-color: {color};'
        f' margin-right: 8px; border: 1px solid #999;"></div>{label}</div>'
        for color, label in LEGEND_ROWS
    )


def _legend_shell(title, check_time, body):
    return f'''
<div style="position: fixed; bottom: 50px; right: 50px;
     background-color: rgba(255, 255, 255, 0.95); border: 2px solid grey;
     border-radius: 8px; padding: 15px; font-family: Arial; font-size: 14px; z-index: 9999;">
  <div style="font-weight: bold; margin-bottom: 8px; font-size: 15px;">{title}</div>
  <div style="font-size: 11px; color: #666; margin-bottom: 10px;">{check_time.strftime('%I:%M %p on %A')}</div>
  {body}
</div>
'''


def status_legend_html(check_time):
    return _legend_shell("Current Parking Status", check_time, _legend_rows_html())


def combined_legend_html(check_time):
    body = f'''
  <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #ddd;">
    <strong style="font-size: 12px;">Parking Zones:</strong>
  </div>
  {_legend_rows_html()}
  <div style="margin: 12px 0 4px; padding-bottom: 4px; border-bottom: 1px solid #ddd;">
    <strong style="font-size: 12px;">Violation Heatmap:</strong>
  </div>
  <div style="font-size: 11px; color: #666;">
    Red = High violations<br>Yellow = Medium violations<br>Green = Low violations
  </div>
'''
    return _legend_shell("Parking Map Legend", check_time, body)


def heatmap_legend_html(check_time, n_hour, n_weekday, n_total, n_clusters):
    low, high = (check_time.hour - HOUR_WINDOW) % 24, (check_time.hour + HOUR_WINDOW) % 24
    body = f'''
  <div style="font-size: 12px; margin-bottom: 8px;">
    Citations issued between <strong>{low:02d}:00</strong> and <strong>{high:02d}:59</strong>
  </div>
  <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #ddd;">
    <strong style="font-size: 12px;">Ticket density:</strong>
  </div>
  <div style="font-size: 11px; color: #666; margin-bottom: 10px;">
    Red = High &nbsp; Yellow = Medium &nbsp; Green = Low
  </div>
  <div style="font-size: 11px; color: #333;">
    This hour, any day: <strong>{n_hour}</strong><br>
    This hour, {check_time:%A}s: <strong>{n_weekday}</strong><br>
    All 90 days: <strong>{n_total}</strong><br>
    Hotspot markers: <strong>{n_clusters}</strong>
  </div>
  <div style="font-size: 10px; color: #888; margin-top: 8px;">
    Toggle layers with the control at top right.
  </div>
'''
    return _legend_shell("Ticket Hotspots Now", check_time, body)


def popup_html(props, is_allowed, hours, check_time):
    status = "✅ PARKING ALLOWED" if is_allowed else "🚫 NO PARKING NOW"
    if not is_allowed:
        current = "No parking"
    elif hours:
        current = f"{hours} hour limit"
    else:
        current = "Unrestricted"

    exceptions = props.get("exceptions", "")
    note = (
        f'<p style="margin: 5px 0; font-size: 11px; color: #0066cc;"><strong>Note:</strong> {exceptions}</p>'
        if exceptions and exceptions != "N/A" else ""
    )
    return f'''
<div style="font-family: Arial; width: 300px;">
    <h4 style="margin: 0 0 10px 0; color: {'#00695c' if is_allowed else '#d32f2f'};">{status}</h4>
    <p style="margin: 5px 0;"><strong>Regulation:</strong> {props.get('regulation') or 'N/A'}</p>
    <p style="margin: 5px 0;"><strong>Days:</strong> {props.get('days') or 'N/A'}</p>
    <p style="margin: 5px 0;"><strong>Hours:</strong> {props.get('from_time') or 'N/A'} - {props.get('to_time') or 'N/A'}</p>
    <p style="margin: 5px 0;"><strong>Current Status:</strong> {current}</p>
    {note}
    <p style="margin: 5px 0; font-size: 11px; color: #666;"><em>As of {check_time.strftime('%I:%M %p')}</em></p>
</div>
'''


def cluster_popup_html(cluster):
    """What a hotspot marker shows when clicked."""
    rows = "".join(
        f'<tr>'
        f'<td style="padding: 2px 8px 2px 0;">{name}</td>'
        f'<td style="padding: 2px 6px 2px 0; text-align: right; white-space: nowrap;"><strong>{n}</strong></td>'
        f'<td style="padding: 2px 0; text-align: right; color: #666; white-space: nowrap;">{pct}%</td>'
        f'</tr>'
        for name, n, pct in cluster["reasons"]
    )
    reasons = f'''
    <div style="margin: 8px 0 4px; font-size: 12px;"><strong>Main reasons for tickets</strong></div>
    <table style="font-size: 11px; border-collapse: collapse; width: 100%;">{rows}</table>
''' if rows else ""

    facts = []
    if cluster["peak_hour"] is not None:
        facts.append(f"Busiest around <strong>{cluster['peak_hour']}:00</strong>"
                     f" on <strong>{cluster['peak_day']}s</strong>")
    if cluster["fine_typical"] is not None:
        facts.append(f"Typical fine <strong>${cluster['fine_typical']:,.0f}</strong>"
                     f" &middot; ${cluster['fine_total']:,.0f} total")
    when = (
        '<div style="margin: 8px 0 0; font-size: 11px; color: #333; line-height: 1.5;">'
        + "<br>".join(facts) + "</div>"
    ) if facts else ""

    addr_items = "".join(
        f'<li>{addr} <span style="color: #666;">({n})</span></li>'
        for addr, n in cluster["addresses"]
    )
    addresses = f'''
    <div style="margin: 8px 0 2px; font-size: 12px;"><strong>Most-cited spots</strong></div>
    <ul style="margin: 2px 0 0; padding-left: 18px; font-size: 11px;">{addr_items}</ul>
''' if addr_items else ""

    return f'''
<div style="font-family: Arial; width: 280px;">
    <h4 style="margin: 0 0 6px 0; color: #d32f2f;">&#128680; Ticket Hotspot</h4>
    <div style="font-size: 13px;">
      <strong>{cluster['count']} citations</strong>
      <span style="color: #666;">&middot; {cluster['share']}% of those shown</span>
    </div>
    {reasons}
    {when}
    {addresses}
</div>
'''


# ============================================
# BUILDERS
# ============================================


def _base_map():
    m = folium.Map(location=USF_CENTER, zoom_start=16)
    folium.plugins.Geocoder(
        collapsed=False, position="bottomleft", placeholder="Search streets, addresses..."
    ).add_to(m)
    m.get_root().html.add_child(folium.Element(GEOCODER_CSS))
    return m


def _add_regulations(target, check_time):
    """Add the regulation polylines to `target`; returns a colour -> count tally."""
    counts = {}
    for feature in zone_features():
        props = feature["properties"]
        lines = to_latlon_lines(feature["geometry"])
        if not lines:
            continue

        is_allowed, hours = is_parking_allowed_now(props, check_time)
        color = get_color_by_availability(is_allowed, hours)
        counts[color] = counts.get(color, 0) + 1

        tooltip = (
            f"{'✅ Available' if is_allowed else '🚫 No parking'}: {hours}hr"
            if hours else "Click for details"
        )
        for line in lines:
            folium.PolyLine(
                locations=line,
                color=color,
                weight=4,
                opacity=1.0,
                popup=folium.Popup(popup_html(props, is_allowed, hours, check_time), max_width=320),
                tooltip=tooltip,
            ).add_to(target)
    return counts


def build_current_status_map(check_time=None):
    """The "Street Parking Hours" map: regulations coloured for `check_time`."""
    check_time = check_time or datetime.now()
    m = _base_map()
    counts = _add_regulations(m, check_time)
    m.get_root().html.add_child(folium.Element(status_legend_html(check_time)))
    return m, {"zones": sum(counts.values()), "colors": counts}


def build_combined_map(check_time=None):
    """The "Combined View" map: live regulations plus the citation heatmap."""
    check_time = check_time or datetime.now()
    m = _base_map()

    regulations = folium.FeatureGroup(name="Parking Regulations", show=True)
    counts = _add_regulations(regulations, check_time)
    regulations.add_to(m)

    stats = {"zones": sum(counts.values()), "colors": counts}

    df = citations()
    if df is not None:
        now_df = this_hour(df, check_time)
        clusters, total = find_clusters(now_df)

        heat_layer(now_df, "Hotspots this hour", show=True).add_to(m)
        heat_layer(df, "Hotspots all hours", show=False).add_to(m)
        cluster_marker_layer(clusters, "Top hotspots now", show=True).add_to(m)

        stats.update(citations_this_hour=len(now_df), citations_total=len(df),
                     clusters_shown=len(clusters), clusters_total=total)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(combined_legend_html(check_time)))
    return m, stats


def build_heatmap_map(check_time=None):
    """The "Heatmap" view: where tickets actually get written at this time of day.

    Built from the live citation feed and filtered to the current hour, with the
    narrower this-hour-this-weekday cut and the full 90 days as toggles.
    """
    check_time = check_time or datetime.now()
    m = _base_map()

    df = citations()
    if df is None:
        m.get_root().html.add_child(folium.Element(
            '<div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%);'
            ' background: rgba(255,255,255,.95); border: 2px solid grey; border-radius: 8px;'
            ' padding: 12px 18px; font-family: Arial; z-index: 9999;">'
            'No citation data yet &mdash; start the backend once to populate the cache.</div>'))
        return m, {"citations_total": 0}

    now_df = this_hour(df, check_time)
    weekday_df = this_hour(df, check_time, same_weekday=True)
    clusters, total = find_clusters(now_df)

    heat_layer(now_df, "This hour, any day", show=True).add_to(m)
    heat_layer(weekday_df, f"This hour, {check_time:%A}s only", show=False).add_to(m)
    heat_layer(df, "All 90 days", show=False).add_to(m)
    cluster_marker_layer(clusters, "Top hotspots now", show=True).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(heatmap_legend_html(
        check_time, len(now_df), len(weekday_df), len(df), len(clusters))))

    return m, {
        "citations_this_hour": len(now_df),
        "citations_this_weekday": len(weekday_df),
        "citations_total": len(df),
        "clusters_shown": len(clusters),
        "clusters_total": total,
    }


# ============================================
# RENDERING (hourly cache)
# ============================================

BUILDERS = {
    "street-hours": (build_current_status_map, "usf_parking_current_status.html"),
    "combined": (build_combined_map, "usf_parking_combined.html"),
    "heatmap": (build_heatmap_map, "usf_parking_heatmap.html"),
}

_render_cache = {}


def render(name, check_time=None):
    """Rendered HTML for a map, cached per hour.

    Regulation windows start and end on the hour, so the colours can only change
    on the hour; anything finer would re-render for no visible difference.
    """
    builder = BUILDERS[name][0]
    now = check_time or datetime.now()
    key = (name, now.date(), now.hour)

    if key not in _render_cache:
        m, stats = builder(now)
        stats = {**stats, "generated": now}
        # Keep both maps for the current hour; drop anything from an earlier one.
        for stale in [k for k in _render_cache if k[1:] != key[1:]]:
            del _render_cache[stale]
        _render_cache[key] = (m.get_root().render(), stats)
    return _render_cache[key]


def save_static(name, check_time=None, output_dir=PUBLIC_MAPS_DIR):
    """Write a map to the React public folder, for serving without the backend."""
    builder, filename = BUILDERS[name]
    m, stats = builder(check_time or datetime.now())
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    m.save(path)
    return path, stats
