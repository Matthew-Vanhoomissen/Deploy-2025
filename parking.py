import random
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import pandas as pd
import json
from shapely import wkt
from shapely.geometry import mapping

app = Flask(__name__, static_folder="frontend/my-app/build", static_url_path="")
CORS(app, origins=["http://localhost:3000"])

# Load real parking data from CSV
print("Loading parking regulations from CSV...")
parking_df = pd.read_csv("data/parking_regulations.csv")  # Update path to your CSV
print(f"✅ Loaded {len(parking_df)} parking regulations")

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/zones')
def zones():
    """
    Return real parking zone data from CSV file.
    Converts shapely geometry to GeoJSON format.
    """
    print("Serving real parking zones from CSV...")
    
    try:
        features = []
        
        # Filter to USF area (optional - remove if you want all data)
        lat_min, lat_max = 37.774, 37.785
        lon_min, lon_max = -122.460, -122.440
        
        for idx, row in parking_df.iterrows():
            try:
                # Parse the geometry from WKT format
                geom = wkt.loads(row['shape'])
                
                # Get centroid to check if it's in USF area
                centroid = geom.centroid
                
                # Filter to USF area (optional)
                if not (lat_min <= centroid.y <= lat_max and lon_min <= centroid.x <= lon_max):
                    continue
                
                # Extract parking hours (handle missing data)
                hrs_begin = row.get('HRS_BEGIN', '')
                hrs_end = row.get('HRS_END', '')
                
                # Convert to string and handle NaN
                hrs_begin = str(int(hrs_begin)) if pd.notna(hrs_begin) and hrs_begin != '' else ''
                hrs_end = str(int(hrs_end)) if pd.notna(hrs_end) and hrs_end != '' else ''
                
                # Get hour limit
                hour_limit = row.get('HRLIMIT', None)
                if pd.notna(hour_limit):
                    try:
                        hour_limit = int(float(hour_limit))
                    except (ValueError, TypeError):
                        hour_limit = None
                else:
                    hour_limit = None
                
                # Create GeoJSON feature
                feature = {
                    "type": "Feature",
                    "geometry": mapping(geom),  # Convert shapely geometry to GeoJSON
                    "properties": {
                        "objectid": row.get('objectid', ''),
                        "regulation": row.get('REGULATION', ''),
                        "days": row.get('DAYS', ''),
                        "hours": row.get('HOURS', ''),
                        "hrs_begin": hrs_begin,
                        "hrs_end": hrs_end,
                        "max_hours": hour_limit,
                        "exceptions": row.get('EXCEPTIONS', ''),
                        "from_time": row.get('FROM_TIME', ''),
                        "to_time": row.get('TO_TIME', ''),
                        "rpparea1": row.get('RPPAREA1', ''),
                        "agency": row.get('AGENCY', ''),
                        "enacted": row.get('ENACTED', ''),
                        "supervisor_district": row.get('supervisor_district', '')
                    }
                }
                
                features.append(feature)
                
            except Exception as e:
                # Skip rows with parsing errors
                print(f"Skipping row {idx}: {e}")
                continue
        
        print(f"✅ Returning {len(features)} parking zones in USF area")
        
        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
        
    except Exception as e:
        print(f"❌ Error in /zones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/zones/all')
def zones_all():
    """
    Return ALL parking zones without filtering to USF area.
    """
    print("Serving ALL parking zones from CSV...")
    
    try:
        features = []
        
        for idx, row in parking_df.iterrows():
            try:
                # Parse the geometry from WKT format
                geom = wkt.loads(row['shape'])
                
                # Extract parking hours
                hrs_begin = row.get('HRS_BEGIN', '')
                hrs_end = row.get('HRS_END', '')
                
                hrs_begin = str(int(hrs_begin)) if pd.notna(hrs_begin) and hrs_begin != '' else ''
                hrs_end = str(int(hrs_end)) if pd.notna(hrs_end) and hrs_end != '' else ''
                
                # Get hour limit
                hour_limit = row.get('HRLIMIT', None)
                if pd.notna(hour_limit):
                    try:
                        hour_limit = int(float(hour_limit))
                    except (ValueError, TypeError):
                        hour_limit = None
                else:
                    hour_limit = None
                
                feature = {
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": {
                        "objectid": row.get('objectid', ''),
                        "regulation": row.get('REGULATION', ''),
                        "days": row.get('DAYS', ''),
                        "hours": row.get('HOURS', ''),
                        "hrs_begin": hrs_begin,
                        "hrs_end": hrs_end,
                        "max_hours": hour_limit,
                        "exceptions": row.get('EXCEPTIONS', ''),
                        "from_time": row.get('FROM_TIME', ''),
                        "to_time": row.get('TO_TIME', ''),
                        "rpparea1": row.get('RPPAREA1', ''),
                        "agency": row.get('AGENCY', ''),
                        "enacted": row.get('ENACTED', ''),
                        "supervisor_district": row.get('supervisor_district', '')
                    }
                }
                
                features.append(feature)
                
            except Exception as e:
                print(f"Skipping row {idx}: {e}")
                continue
        
        print(f"✅ Returning {len(features)} total parking zones")
        
        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
        
    except Exception as e:
        print(f"❌ Error in /zones/all: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/tickets')
def tickets():
    """
    Placeholder for ticket data endpoint.
    """
    print("Serving sample parking tickets...")
    
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


if __name__ == '__main__':
    app.run(debug=True, port=5001)