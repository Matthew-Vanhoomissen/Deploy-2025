from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import requests
import random
import json
import pandas as pd
from sklearn.cluster import DBSCAN
from xgboost import XGBClassifier
import datetime


app = Flask(__name__, static_folder="frontend/my-app/build", static_url_path="")
CORS(app, origins=["http://localhost:3000"])

with open("data/sf_streets.json", "r") as f:
    street_data = json.load(f)
    centerlines = street_data["features"]


#ML starting load and prepare data when server starts
df = pd.read_csv("citations.csv", parse_dates=["issue_datetime"])
df = df.dropna(subset=["latitude", "longitude"])

coords = df[["latitude", "longitude"]].to_numpy()
db = DBSCAN(eps=0.002, min_samples=10).fit(coords)
df["zone_id"] = db.labels_

zones = df.groupby("zone_id")[["latitude", "longitude"]].mean().reset_index()

df["hour"] = df["issue_datetime"].dt.hour
df["dayofweek"] = df["issue_datetime"].dt.dayofweek
df["month"] = df["issue_datetime"].dt.month

recent = (df.groupby(["zone_id", "hour", "dayofweek"])
          .size()
          .reset_index(name="ticket_count"))

recent = recent[recent["zone_id"] != -1]

x = recent[["hour", "dayofweek"]]
y = recent["zone_id"]

model = XGBClassifier(tree_method="hist", max_depth=5)
model.fit(x,y)


# NEW HELPER FUNCTIONS FOR FOLIUM
def get_max_hours(properties):
    """Determine parking hours from properties"""
    if 'max_hours' in properties and properties['max_hours'] is not None:
        return properties['max_hours']
    
    begin = properties.get('hrs_begin') or properties.get('HRS_BEGIN', '')
    end = properties.get('hrs_end') or properties.get('HRS_END', '')
    
    try:
        begin_num = int(begin) if begin else 0
        end_num = int(end) if end else 0
        
        if begin_num > 0 and end_num > 0:
            begin_hours = begin_num // 100 + (begin_num % 100) / 60
            end_hours = end_num // 100 + (end_num % 100) / 60
            duration = end_hours - begin_hours
            if duration > 0:
                return duration
    except (ValueError, TypeError):
        pass
    
    rule = (properties.get('regulation') or properties.get('REGULATION') or '').upper()
    
    if any(x in rule for x in ['NO PARKING', 'TOW-AWAY', 'NO STOPPING']):
        return 0
    
    if '1 HR' in rule or '1HR' in rule or '1 HOUR' in rule:
        return 1
    if '2 HR' in rule or '2HR' in rule or '2 HOUR' in rule:
        return 2
    if '3 HR' in rule or '3HR' in rule or '3 HOUR' in rule:
        return 3
    if '4 HR' in rule or '4HR' in rule or '4 HOUR' in rule:
        return 4
    
    return None

def get_color_by_hours(hours):
    """Get color based on parking hours"""
    if hours is None:
        return "#808080"  # Gray - Unknown
    if hours <= 0:
        return "#FF0000"  # Red - No Parking
    elif hours == 1:
        return "#FFFF00"  # Yellow - 1 Hour
    elif hours == 2:
        return "#FFA500"  # Orange - 2 Hours
    else:
        return "#00FF00"  # Green - 3+ Hours


@app.route('/predict')
def predict_metermaid():
    now = datetime.datetime.now()
    hour = now.hour
    dayofweek = now.weekday()

    pred_zone = model.predict([[hour, dayofweek]])[0]
    zone_cords = zones[zones["zone_id"] == pred_zone][["latitude", "longitude"]].values[0].tolist()

    return jsonify({
        "zone_id": int(pred_zone),
        "latitude": zone_cords[0],
        "longitude": zone_cords[1]
    })

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/zones')
def zones_endpoint():
    """
    Generate sample parking zone data around USFCA since the SF API is broken.
    In production, this would use real API data.
    """
    print("Generating sample parking zones around USFCA...")
    
    # USFCA coordinates: 37.7765, -122.4505
    # Generate sample street segments in a grid around USFCA
    try:

        features = []
        lat_min, lat_max = 37.774, 37.785
        lon_min, lon_max = -122.460, -122.440
        
        # Sample regulations with different time limits
        regulations = [
            ("NO PARKING 8AM-6PM", 0),
            ("2 HR PARKING 9AM-6PM", 2),
            ("1 HR PARKING 9AM-6PM", 1),
            ("4 HR PARKING 9AM-6PM", 4),
            ("STREET CLEANING THU 12PM-2PM", 0),
        ]
        
        # Generate streets in a grid around USFCA
        
        for feature in centerlines:
            coords = feature["geometry"]["coordinates"]

            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            centroid_lat = sum(lats) / len(lats) 
            centroid_lon = sum(lons) / len(lons)

            if (lat_min <= centroid_lat <= lat_max) and (lon_min <= centroid_lon <= lon_max):
                regulation, hours = random.choice(regulations)
                feat = {
                    "type": "Feature",
                    "geometry": feature["geometry"],
                    "properties": {
                        "regulation": regulation,
                        "days": "MON_FRI",
                        "hrs_begin": "900" if hours > 0 else "",
                        "hrs_end": "1800" if hours > 0 else "",
                        "max_hours": hours
                    }
                }
                features.append(feat)

        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
    except Exception as e:
        print("Error in /zones", e)
        return jsonify({"error": str(e)}), 500


# NEW ROUTE FOR FOLIUM - Returns GeoJSON with color information
@app.route('/parking-geojson')
def parking_geojson():
    """
    Return GeoJSON with color information that can be loaded into Folium
    """
    try:
        lat_min, lat_max = 37.774, 37.785
        lon_min, lon_max = -122.460, -122.440
        
        regulations = [
            ("NO PARKING 8AM-6PM", 0),
            ("2 HR PARKING 9AM-6PM", 2),
            ("1 HR PARKING 9AM-6PM", 1),
            ("4 HR PARKING 9AM-6PM", 4),
            ("STREET CLEANING THU 12PM-2PM", 0),
        ]
        
        features = []
        
        for feature in centerlines:
            coords = feature["geometry"]["coordinates"]
            
            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            centroid_lat = sum(lats) / len(lats)
            centroid_lon = sum(lons) / len(lons)
            
            if (lat_min <= centroid_lat <= lat_max) and (lon_min <= centroid_lon <= lon_max):
                regulation, hours = random.choice(regulations)
                
                color = get_color_by_hours(hours)
                
                feat = {
                    "type": "Feature",
                    "geometry": feature["geometry"],
                    "properties": {
                        "regulation": regulation,
                        "days": "MON_FRI",
                        "hrs_begin": "900" if hours > 0 else "",
                        "hrs_end": "1800" if hours > 0 else "",
                        "max_hours": hours,
                        "color": color  # Add color to properties
                    }
                }
                features.append(feat)
        
        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
        
    except Exception as e:
        print("Error in /parking-geojson", e)
        return jsonify({"error": str(e)}), 500


@app.route('/tickets')
def tickets():
    """
    Generate sample parking ticket locations around USFCA.
    In production, this would use real ticket data.
    """
    print("Generating sample parking tickets around USFCA...")
    
    # Generate random ticket locations around USFCA
    points = []
    lat_center = 37.7765
    lon_center = -122.4505
    
    for _ in range(200):
        # Random offset within ~0.5km
        lat = lat_center + (random.random() - 0.5) * 0.01
        lon = lon_center + (random.random() - 0.5) * 0.01
        points.append([lat, lon])
    
    print(f"✓ Generated {len(points)} sample ticket locations")
    return jsonify(points)

@app.route('/real-api-test')
def real_api_test():
    """
    Test endpoint to check if SF API is working.
    Try a different dataset that might work.
    """
    try:
        # Try SF 311 cases instead (usually more reliable)
        url = "https://data.sfgov.org/resource/vw6y-z8j6.json"
        params = {"$limit": 5}
        
        print(f"Testing SF API with: {url}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return jsonify({
            "status": "success",
            "message": "SF API is working!",
            "sample_data": data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "SF API is not responding properly",
            "error": str(e)
        }), 500

@app.route('/debug')
def debug():
    """Debug endpoint"""
    try:
        # Try the parking API one more time
        url = "https://data.sfgov.org/api/v3/views/hi6h-neyh/query.geojson"
        params = {"$limit": 2}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return jsonify({
            "status": "received_response",
            "record_count": len(data),
            "records": data,
            "message": "API returned empty objects - dataset is broken" if all(not d for d in data) else "API working"
        })
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)