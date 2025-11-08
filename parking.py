from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import requests
import random
import json

app = Flask(__name__, static_folder="frontend/my-app/build", static_url_path="")
CORS(app, origins=["http://localhost:3000"])

with open("data/sf_streets.json", "r") as f:
    street_data = json.load(f)
    centerlines = street_data["features"]

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/zones')
def zones():
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