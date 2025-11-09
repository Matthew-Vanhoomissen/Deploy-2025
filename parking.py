from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import json
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import GradientBoostingClassifier
from xgboost import XGBClassifier
import datetime
import random

# Looks at the current hour and current day of week.
# If you are in a peak hour AND peak day (most tickets historically happen then), the score is multiplied by 1.5.
# If you are in a peak hour OR peak day, it’s multiplied by 1.2.
# Then capped at 100.

app = Flask(__name__, static_folder="frontend/my-app/build", static_url_path="")
CORS(app, origins=["http://localhost:3000"])

# Load street centerlines for Folium map
with open("data/sf_streets.json", "r") as f:
    street_data = json.load(f)
    centerlines = street_data["features"]

# ============================================
# LOAD AND GEOCODE DATA
# ============================================

df = pd.read_csv("citations_geocoded.csv")

# Ensure lat/lon columns exist
if "latitude" not in df.columns:
    df["latitude"] = None
if "longitude" not in df.columns:
    df["longitude"] = None

# Convert issue_datetime to datetime object
if "issue_datetime" not in df.columns:
    # Combine issue_date + issue_time if issue_datetime is missing
    df['issue_datetime'] = pd.to_datetime(df['issue_date'] + " " + df['issue_time'])
else:
    df['issue_datetime'] = pd.to_datetime(df['issue_datetime'])

df = df.dropna(subset=["latitude", "longitude"])
df = df.sort_values('issue_datetime')

# ============================================
# CREATE ZONES USING DBSCAN
# ============================================

coords = df[["latitude", "longitude"]].to_numpy()
db = DBSCAN(eps=0.002, min_samples=10).fit(coords)
df["zone_id"] = db.labels_

# Time features
df["hour"] = df["issue_datetime"].dt.hour
df["dayofweek"] = df["issue_datetime"].dt.dayofweek
df["month"] = df["issue_datetime"].dt.month
df["is_weekend"] = df["dayofweek"].isin([5, 6]).astype(int)

# ============================================
# RISK SCORE MODELS
# ============================================

print("Training risk score models...")

total_days = (df['issue_datetime'].max() - df['issue_datetime'].min()).days
if total_days < 1:
    total_days = 1

# Aggregate statistics per zone
zone_stats = df[df["zone_id"] != -1].groupby("zone_id").agg({
    'zone_id': 'count',
    'hour': lambda x: x.mode()[0] if len(x) > 0 else 12,
    'dayofweek': lambda x: x.mode()[0] if len(x) > 0 else 2
}).rename(columns={'zone_id': 'total_tickets', 'hour': 'peak_hour', 'dayofweek': 'peak_day'})

zones = df[df["zone_id"] != -1].groupby("zone_id")[["latitude", "longitude"]].mean()
zone_stats = zone_stats.join(zones)
zone_stats['tickets_per_day'] = zone_stats['total_tickets'] / total_days
max_tickets = zone_stats['tickets_per_day'].max()
zone_stats['base_risk_score'] = (zone_stats['tickets_per_day'] / max_tickets * 100).round(1) if max_tickets > 0 else 0

# Time-based risk model
time_risk = df[df["zone_id"] != -1].groupby(
    ["zone_id", "hour", "dayofweek", "is_weekend"]
).size().reset_index(name='tickets')

zone_totals = df[df["zone_id"] != -1].groupby("zone_id").size().to_dict()
time_risk['zone_total'] = time_risk['zone_id'].map(zone_totals)
time_risk['ticket_rate'] = (time_risk['tickets'] / time_risk['zone_total'] * 100)

X_risk = time_risk[["zone_id", "hour", "dayofweek", "is_weekend"]]
y_risk = pd.cut(time_risk['ticket_rate'], bins=[0, 10, 30, 100], labels=[0, 1, 2])

model_risk = GradientBoostingClassifier(n_estimators=50, max_depth=4, random_state=42)
model_risk.fit(X_risk, y_risk)

# Original XGBoost for backward compatibility
recent = df.groupby(["zone_id", "hour", "dayofweek"]).size().reset_index(name="ticket_count")
recent = recent[recent["zone_id"] != -1]
x = recent[["hour", "dayofweek"]]
y = recent["zone_id"]
model = XGBClassifier(tree_method="hist", max_depth=5)
model.fit(x, y)

print(f"✓ Risk scoring model trained on {len(zone_stats)} zones")
print(f"✓ Data period: {total_days} days")

# ============================================
# HELPER FUNCTION
# ============================================

def categorize_risk(score):
    if score < 10:
        return "Low", "#00FF00", "✅ Safe to park here"
    elif score > 10 and score  < 30:
        return "Medium", "#FFA500", "⚠️ Park with caution"
    else:
        return "High", "#FF0000", "🚨 Avoid parking here"

# ============================================
# FLASK ENDPOINTS
# ============================================

@app.route('/risk-score/<int:zone_id>')
def get_zone_risk_score(zone_id):
    now = datetime.datetime.now()
    hour = now.hour
    dayofweek = now.weekday()
    is_weekend = 1 if dayofweek in [5, 6] else 0

    if zone_id not in zone_stats.index:
        return jsonify({'error': 'Zone not found'}), 404

    stats = zone_stats.loc[zone_id]

    # Adjust risk score based on current time
    adjusted_score = float(stats['base_risk_score'])
    is_peak_hour = abs(hour - stats['peak_hour']) <= 1
    is_peak_day = dayofweek == stats['peak_day']

    if is_peak_hour and is_peak_day:
        adjusted_score *= 1.5
    elif is_peak_hour or is_peak_day:
        adjusted_score *= 1.2
    adjusted_score = min(100, adjusted_score)

    risk_level, risk_color, recommendation = categorize_risk(adjusted_score)

    return jsonify({
        'zone_id': int(zone_id),
        'timestamp': now.isoformat(),
        'risk_score': round(adjusted_score, 1),
        'risk_level': risk_level,
        'risk_color': risk_color,
        'recommendation': recommendation,
        'is_peak_time': bool(is_peak_hour and is_peak_day),
        'peak_info': {
            'hour': int(stats['peak_hour']),
            'day': ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][int(stats['peak_day'])]
        },
        'statistics': {
            'total_tickets': int(stats['total_tickets']),
            'tickets_per_day': round(float(stats['tickets_per_day']), 2),
            'data_period_days': total_days
        },
        'location': {
            'latitude': float(stats['latitude']),
            'longitude': float(stats['longitude'])
        }
    })

@app.route('/safest-zones')
def get_safest_zones():
    now = datetime.datetime.now()
    hour = now.hour
    dayofweek = now.weekday()

    zones_list = []
    for zone_id in zone_stats.index:
        if zone_id == -1:
            continue
        stats = zone_stats.loc[zone_id]
        adjusted_score = float(stats['base_risk_score'])
        is_peak_hour = abs(hour - stats['peak_hour']) <= 1
        is_peak_day = dayofweek == stats['peak_day']

        if is_peak_hour and is_peak_day:
            adjusted_score *= 1.5
        elif is_peak_hour or is_peak_day:
            adjusted_score *= 1.2
        adjusted_score = min(100, adjusted_score)
        risk_level, _, _ = categorize_risk(adjusted_score)

        zones_list.append({
            'zone_id': int(zone_id),
            'risk_score': round(adjusted_score, 1),
            'risk_level': risk_level,
            'latitude': float(stats['latitude']),
            'longitude': float(stats['longitude'])
        })

    zones_list.sort(key=lambda x: x['risk_score'])
    return jsonify({'timestamp': now.isoformat(), 'safest_zones': zones_list[:5]})

@app.route('/danger-zones')
def get_danger_zones():
    now = datetime.datetime.now()
    hour = now.hour
    dayofweek = now.weekday()

    zones_list = []
    for zone_id in zone_stats.index:
        if zone_id == -1:
            continue
        stats = zone_stats.loc[zone_id]
        adjusted_score = float(stats['base_risk_score'])
        is_peak_hour = abs(hour - stats['peak_hour']) <= 1
        is_peak_day = dayofweek == stats['peak_day']

        if is_peak_hour and is_peak_day:
            adjusted_score *= 1.5
        elif is_peak_hour or is_peak_day:
            adjusted_score *= 1.2
        adjusted_score = min(100, adjusted_score)
        risk_level, _, _ = categorize_risk(adjusted_score)

        zones_list.append({
            'zone_id': int(zone_id),
            'risk_score': round(adjusted_score, 1),
            'risk_level': risk_level,
            'latitude': float(stats['latitude']),
            'longitude': float(stats['longitude'])
        })

    zones_list.sort(key=lambda x: x['risk_score'], reverse=True)
    return jsonify({'timestamp': now.isoformat(), 'danger_zones': zones_list[:5]})

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
