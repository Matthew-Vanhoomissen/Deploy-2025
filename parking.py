import random
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import pandas as pd
import json
from shapely import wkt
from shapely.geometry import mapping
import folium
import folium.plugins
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__, static_folder="frontend/my-app/build", static_url_path="")
CORS(app, origins=["http://localhost:3000"])

# Install required packages if missing
try:
    from folium.plugins import HeatMap
    from sklearn.cluster import DBSCAN
    import numpy as np
except ImportError as e:
    print(f"⚠️ Warning: Missing package for combined map generation: {e}")
    print("Run: pip install scikit-learn")

# Load real parking data from CSV
print("Loading parking regulations from CSV...")
parking_df = pd.read_csv("data/parking_regulations.csv")
print(f"✅ Loaded {len(parking_df)} parking regulations")

# === MAP GENERATION FUNCTIONS ===

def get_max_hours(properties):
    """Helper function to determine parking hours"""
    if 'max_hours' in properties and properties['max_hours'] is not None:
        return properties['max_hours']
    
    begin = properties.get('hrs_begin') or properties.get('HRS_BEGIN')
    end = properties.get('hrs_end') or properties.get('HRS_END')
    
    if begin and end:
        try:
            begin = int(begin)
            end = int(end)
            begin_hours = begin // 100 + (begin % 100) / 60
            end_hours = end // 100 + (end % 100) / 60
            duration = end_hours - begin_hours
            if duration > 0:
                return duration
        except (ValueError, TypeError):
            pass
    
    rule = str(properties.get('regulation') or properties.get('REGULATION') or '').upper()
    
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

def is_parking_allowed_now(properties, check_time=None):
    if check_time is None:
        check_time = datetime.now()
    
    current_day = check_time.weekday()
    day_names = ['M', 'TU', 'W', 'TH', 'F', 'SA', 'SU']
    current_day_name = day_names[current_day]
    
    current_time_int = check_time.hour * 100 + check_time.minute
    
    days = str(properties.get('days') or properties.get('DAYS') or '').upper()
    begin = properties.get('hrs_begin') or properties.get('HRS_BEGIN')
    end = properties.get('hrs_end') or properties.get('HRS_END')
    regulation = str(properties.get('regulation') or properties.get('REGULATION') or '').upper()
    
    if days:
        if 'M-F' in days:
            if current_day >= 5:
                return (True, None)
        elif 'M-SA' in days:
            if current_day == 6:
                return (True, None)
        elif 'SA-SU' in days or days == 'SA' or days == 'SU':
            if current_day < 5:
                return (True, None)
        elif current_day_name not in days and 'DAILY' not in days:
            return (True, None)
    
    if begin and end:
        try:
            begin_int = int(begin)
            end_int = int(end)
            
            if current_time_int < begin_int or current_time_int > end_int:
                return (True, None)
            else:
                if 'NO PARKING' in regulation or 'TOW-AWAY' in regulation:
                    return (False, 0)
                else:
                    hours = get_max_hours(properties)
                    return (True, hours)
        except (ValueError, TypeError):
            pass
    
    if 'NO PARKING' in regulation or 'TOW-AWAY' in regulation:
        return (False, 0)
    
    hours = get_max_hours(properties)
    return (True, hours)

def get_color_by_availability(is_allowed, hours):
    if not is_allowed:
        return "#FF0000"
    if hours is None:
        return "#00FF00"
    if hours <= 0:
        return "#FF0000"
    elif hours == 1:
        return "#FFFF00"
    elif hours == 2:
        return "#FFA500"
    else:
        return "#00FF00"

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two lat/lon points"""
    from math import radians, sin, cos, sqrt, atan2
    R = 3959  # Earth's radius in miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def generate_parking_map():
    """Generate the parking status map based on current time"""
    check_time = datetime.now()
    print(f"🕐 Generating map for: {check_time.strftime('%A, %B %d, %Y at %I:%M %p')}")
    
    # Create base map centered on USF
    usf_center = [37.7765, -122.4505]
    m = folium.Map(location=usf_center, zoom_start=16)
    
    # Add search bar
    folium.plugins.Geocoder(
        collapsed=False,
        position='bottomleft',
        placeholder='Search streets, addresses...'
    ).add_to(m)
    
    custom_css = """
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
    .leaflet-control-geocoder-form {
        width: 100% !important;
        display: flex !important;
        gap: 10px !important;
    }
    .leaflet-control-geocoder-form input {
        flex: 1 !important;
        background: rgba(255, 255, 255, 0.25) !important;
        border-radius: 1.5rem !important;
        padding: 10px 14px !important;
        font-size: 1.1rem !important;
        color: #f1f1f1 !important;
    }
    .leaflet-control-geocoder-form input::placeholder {
        color: rgba(255, 255, 255, 0.85) !important;
    }
    .leaflet-control-geocoder-icon {
        display: none !important;
    }
    .leaflet-control-geocoder-alternatives {
        max-height: 150px !important;
        overflow-y: auto !important;
        background: rgba(0, 77, 64, 0.85) !important;
        border-radius: 1rem !important;
    }
    .leaflet-control-geocoder-alternatives li:hover {
        background: rgba(76, 175, 80, 0.25) !important;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(custom_css))
    
    # Get zones data
    try:
        features = []
        lat_min, lat_max = 37.774, 37.785
        lon_min, lon_max = -122.460, -122.440
        
        for idx, row in parking_df.iterrows():
            try:
                geom = wkt.loads(row['shape'])
                centroid = geom.centroid
                
                if not (lat_min <= centroid.y <= lat_max and lon_min <= centroid.x <= lon_max):
                    continue
                
                hrs_begin = str(int(row.get('HRS_BEGIN', ''))) if pd.notna(row.get('HRS_BEGIN')) else ''
                hrs_end = str(int(row.get('HRS_END', ''))) if pd.notna(row.get('HRS_END')) else ''
                
                hour_limit = row.get('HRLIMIT', None)
                if pd.notna(hour_limit):
                    try:
                        hour_limit = int(float(hour_limit))
                    except (ValueError, TypeError):
                        hour_limit = None
                
                props = {
                    "regulation": row.get('REGULATION', ''),
                    "days": row.get('DAYS', ''),
                    "hrs_begin": hrs_begin,
                    "hrs_end": hrs_end,
                    "max_hours": hour_limit,
                    "exceptions": row.get('EXCEPTIONS', ''),
                    "from_time": row.get('FROM_TIME', ''),
                    "to_time": row.get('TO_TIME', '')
                }
                
                is_allowed, hours = is_parking_allowed_now(props, check_time)
                color = get_color_by_availability(is_allowed, hours)
                
                # Convert geometry to coordinates
                geom_dict = mapping(geom)
                coords = geom_dict['coordinates']
                
                if geom_dict['type'] == 'LineString':
                    line_coords = [[coord[1], coord[0]] for coord in coords]
                elif geom_dict['type'] == 'MultiLineString':
                    line_coords = []
                    for line in coords:
                        line_coords.extend([[coord[1], coord[0]] for coord in line])
                else:
                    continue
                
                if not line_coords or len(line_coords) < 2:
                    continue
                
                status = "✅ PARKING ALLOWED" if is_allowed else "🚫 NO PARKING NOW"
                popup_html = f"""
                <div style="font-family: Arial; width: 300px;">
                    <h4 style="margin: 0 0 10px 0; color: {'#00695c' if is_allowed else '#d32f2f'};">{status}</h4>
                    <p style="margin: 5px 0;"><strong>Regulation:</strong> {props.get('regulation', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Days:</strong> {props.get('days', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Hours:</strong> {props.get('from_time', 'N/A')} - {props.get('to_time', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Current Status:</strong> {f"{hours} hour limit" if hours and is_allowed else "No parking" if not is_allowed else "Unrestricted"}</p>
                    <p style="margin: 5px 0; font-size: 11px; color: #666;"><em>As of {check_time.strftime('%I:%M %p')}</em></p>
                </div>
                """
                
                folium.PolyLine(
                    locations=line_coords,
                    color=color,
                    weight=4,
                    opacity=1.0,
                    popup=folium.Popup(popup_html, max_width=320),
                    tooltip=f"{'✅ Available' if is_allowed else '🚫 No parking'}: {hours}hr" if hours else "Click for details"
                ).add_to(m)
                
            except Exception as e:
                continue
        
        print(f"✅ Added parking zones to map")
        
    except Exception as e:
        print(f"❌ Error processing zones: {e}")
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; 
         bottom: 50px; right: 50px; 
         background-color: rgba(255, 255, 255, 0.95);
         border: 2px solid grey;
         border-radius: 8px;
         padding: 15px;
         font-family: Arial;
         font-size: 14px;
         z-index: 9999;">
         
    <div style="font-weight: bold; margin-bottom: 8px; font-size: 15px;">
        Current Parking Status
    </div>
    <div style="font-size: 11px; color: #666; margin-bottom: 10px;">
        {check_time.strftime('%I:%M %p on %A')}
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <div style="width: 18px; height: 18px; background-color: #FF0000; margin-right: 8px; border: 1px solid #999;"></div>
        No Parking Now
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <div style="width: 18px; height: 18px; background-color: #FFFF00; margin-right: 8px; border: 1px solid #999;"></div>
        1 Hour Limit
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <div style="width: 18px; height: 18px; background-color: #FFA500; margin-right: 8px; border: 1px solid #999;"></div>
        2 Hour Limit
    </div>

    <div style="display: flex; align-items: center;">
        <div style="width: 18px; height: 18px; background-color: #00FF00; margin-right: 8px; border: 1px solid #999;"></div>
        3+ Hours / Unrestricted
    </div>

    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save to the public maps folder
    output_file = "frontend/my-app/public/maps/usf_parking_current_status.html"
    m.save(output_file)
    
    # Ensure file is fully written to disk
    import os
    import time
    time.sleep(0.2)  # Small delay to ensure file is flushed
    
    # Verify file exists and is not empty
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        print(f"✅ Map saved to {output_file} ({os.path.getsize(output_file)} bytes)")
    else:
        print(f"⚠️ Warning: File may not be properly saved")
    
    return check_time

def generate_combined_map():
    """Generate the combined parking map with zones + heatmap based on current time"""
    from folium.plugins import HeatMap
    from sklearn.cluster import DBSCAN
    import numpy as np
    
    check_time = datetime.now()
    usf_center = [37.7765, -122.4505]
    
    print(f"🗺️  Generating combined parking map...")
    print(f"🕐 Time: {check_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n")
    
    # Create base map
    m = folium.Map(location=usf_center, zoom_start=16)
    
    # Add search bar with same styling as other maps
    folium.plugins.Geocoder(
        collapsed=False,
        position='bottomleft',
        placeholder='Search streets, addresses...'
    ).add_to(m)
    
    custom_css = """
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
    .leaflet-control-geocoder-form {
        width: 100% !important;
        display: flex !important;
        gap: 10px !important;
    }
    .leaflet-control-geocoder-form input {
        flex: 1 !important;
        background: rgba(255, 255, 255, 0.25) !important;
        border-radius: 1.5rem !important;
        padding: 10px 14px !important;
        font-size: 1.1rem !important;
        color: #f1f1f1 !important;
    }
    .leaflet-control-geocoder-form input::placeholder {
        color: rgba(255, 255, 255, 0.85) !important;
    }
    .leaflet-control-geocoder-icon {
        display: none !important;
    }
    .leaflet-control-geocoder-alternatives {
        max-height: 150px !important;
        overflow-y: auto !important;
        background: rgba(0, 77, 64, 0.85) !important;
        border-radius: 1rem !important;
    }
    .leaflet-control-geocoder-alternatives li:hover {
        background: rgba(76, 175, 80, 0.25) !important;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(custom_css))
    
    # Add parking zones
    print("\n📍 Loading parking zones...")
    try:
        lat_min, lat_max = 37.774, 37.785
        lon_min, lon_max = -122.460, -122.440
        
        allowed_count = 0
        restricted_count = 0
        
        for idx, row in parking_df.iterrows():
            try:
                geom = wkt.loads(row['shape'])
                centroid = geom.centroid
                
                if not (lat_min <= centroid.y <= lat_max and lon_min <= centroid.x <= lon_max):
                    continue
                
                hrs_begin = str(int(row.get('HRS_BEGIN', ''))) if pd.notna(row.get('HRS_BEGIN')) else ''
                hrs_end = str(int(row.get('HRS_END', ''))) if pd.notna(row.get('HRS_END')) else ''
                
                hour_limit = row.get('HRLIMIT', None)
                if pd.notna(hour_limit):
                    try:
                        hour_limit = int(float(hour_limit))
                    except (ValueError, TypeError):
                        hour_limit = None
                
                props = {
                    "regulation": row.get('REGULATION', ''),
                    "days": row.get('DAYS', ''),
                    "hrs_begin": hrs_begin,
                    "hrs_end": hrs_end,
                    "max_hours": hour_limit,
                    "exceptions": row.get('EXCEPTIONS', ''),
                    "from_time": row.get('FROM_TIME', ''),
                    "to_time": row.get('TO_TIME', '')
                }
                
                is_allowed, hours = is_parking_allowed_now(props, check_time)
                color = get_color_by_availability(is_allowed, hours)
                
                if is_allowed:
                    allowed_count += 1
                else:
                    restricted_count += 1
                
                geom_dict = mapping(geom)
                coords = geom_dict['coordinates']
                
                if geom_dict['type'] == 'LineString':
                    line_coords = [[coord[1], coord[0]] for coord in coords]
                elif geom_dict['type'] == 'MultiLineString':
                    line_coords = []
                    for line in coords:
                        line_coords.extend([[coord[1], coord[0]] for coord in line])
                else:
                    continue
                
                if not line_coords or len(line_coords) < 2:
                    continue
                
                status = "✅ PARKING ALLOWED" if is_allowed else "🚫 NO PARKING NOW"
                popup_html = f"""
                <div style="font-family: Arial; width: 300px;">
                    <h4 style="margin: 0 0 10px 0; color: {'#00695c' if is_allowed else '#d32f2f'};">{status}</h4>
                    <p style="margin: 5px 0;"><strong>Regulation:</strong> {props.get('regulation', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Days:</strong> {props.get('days', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Hours:</strong> {props.get('from_time', 'N/A')} - {props.get('to_time', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Current Status:</strong> {f"{hours} hour limit" if hours and is_allowed else "No parking" if not is_allowed else "Unrestricted"}</p>
                    <p style="margin: 5px 0; font-size: 11px; color: #666;"><em>As of {check_time.strftime('%I:%M %p')}</em></p>
                </div>
                """
                
                folium.PolyLine(
                    locations=line_coords,
                    color=color,
                    weight=4,
                    opacity=1.0,
                    popup=folium.Popup(popup_html, max_width=320),
                    tooltip=f"{'✅ Available' if is_allowed else '🚫 No parking'}: {hours}hr" if hours else "Click for details"
                ).add_to(m)
                
            except Exception as e:
                continue
        
        print(f"✅ Parking zones processed: {allowed_count} allowed, {restricted_count} restricted")
        
    except Exception as e:
        print(f"❌ Error processing zones: {e}")
    
    # Add heatmap layer
    print("\n📊 Loading parking ticket data...")
    try:
        df = pd.read_csv("data/tickets_with_coords.csv")
        df = df[(df["latitude"].notna()) & (df["longitude"].notna())]
        df = df[(df["latitude"] != 0) & (df["longitude"] != 0)]
        
        # Rename violation descriptions
        df['violation_desc'] = df['violation_desc'].str.replace('STR CLEAN', 'Parked During Street Cleaning')
        df['violation_desc'] = df['violation_desc'].str.replace('PRK PROHIB', 'Parking Prohibited Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('PKG PROHIB', 'Parking Prohibited Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('NO PRK ZN', 'No Parking Zone Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('DISOB SIGN', 'Disobeying Sign Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('NO PERMIT', 'No Permit Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('TMP PK RES', 'Temp Parking Restriction Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('METER DTN', 'Downtown Meter Expire Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('MTR OUT DT', 'Expired Meter Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('FIRE HYD', 'Parked By Fire Hydrant Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('RED ZONE', 'Parked In Safety/Bus Lane')
        df['violation_desc'] = df['violation_desc'].str.replace('YEL ZONE', 'Parked In Loading Zone')
        df['violation_desc'] = df['violation_desc'].str.replace('WHITE ZONE', 'Parked In Pick-up/Drop-off Zone')
        df['violation_desc'] = df['violation_desc'].str.replace('GREEN ZONE', 'Parked In Short-term Parking')
        df['violation_desc'] = df['violation_desc'].str.replace('BLK BIKE L', 'Blocked Bike Lane Violation')
        df['violation_desc'] = df['violation_desc'].str.replace('BL ZNE BLK', 'Parked In Disabled Parking')
        df['violation_desc'] = df['violation_desc'].str.replace('SAFE/RED Z', 'Stopped In No Stopping Zone')
        
        # Filter to within 1 mile of USF
        df['distance_miles'] = df.apply(
            lambda row: haversine_distance(usf_center[0], usf_center[1], 
                                          row['latitude'], row['longitude']),
            axis=1
        )
        df = df[df['distance_miles'] <= 1.0]
        
        heat_data = [[row['latitude'], row['longitude']] for idx, row in df.iterrows()]
        
        # Add heatmap
        HeatMap(
            heat_data,
            name='Violation Hotspots',
            radius=10,
            blur=5,
            max_zoom=1,
            min_opacity=0.3,
            max_opacity=0.9,
            gradient={
                0.0: 'rgba(0,0,255,0)',
                0.3: 'green',
                0.6: 'yellow', 
                1.0: 'red'
            }
        ).add_to(m)
        
        print(f"✅ Added {len(heat_data)} ticket locations to heatmap")
        
        # Find clusters using DBSCAN
        coords = df[['latitude', 'longitude']].values
        clustering = DBSCAN(eps=0.0002, min_samples=10).fit(coords)
        df['cluster'] = clustering.labels_
        
        # Add clickable markers for significant clusters
        cluster_counts = df[df['cluster'] != -1].groupby('cluster').size()
        significant_clusters = cluster_counts[cluster_counts >= 15]
        
        for cluster_id in significant_clusters.index:
            cluster_data = df[df['cluster'] == cluster_id]
            count = len(cluster_data)
            
            center_lat = cluster_data['latitude'].mean()
            center_lon = cluster_data['longitude'].mean()
            
            top_violations = cluster_data['violation_desc'].value_counts().head(3)
            
            popup_html = f"""
            <div style="font-family: Arial; width: 250px;">
                <h4 style="margin: 0 0 10px 0; color: #d32f2f;">🚨 Cluster #{cluster_id}</h4>
                <p style="margin: 5px 0;"><strong>{count} violations</strong></p>
                <hr style="margin: 10px 0;">
                <p style="margin: 5px 0; font-size: 12px;"><strong>Top violations:</strong></p>
                <ul style="margin: 5px 0; padding-left: 20px; font-size: 11px;">
            """
            
            for violation, vcount in top_violations.items():
                popup_html += f"<li>{violation[:40]}... ({vcount})</li>"
            
            popup_html += "</ul></div>"
            
            folium.CircleMarker(
                location=[center_lat, center_lon],
                radius=6,
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Cluster: {count} violations (click for details)"
            ).add_to(m)
        
        print(f"✅ Added {len(significant_clusters)} violation clusters")
        
    except Exception as e:
        print(f"⚠️  Could not load ticket data: {e}")
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; 
         bottom: 50px; right: 50px; 
         background-color: rgba(255, 255, 255, 0.95);
         border: 2px solid grey;
         border-radius: 8px;
         padding: 15px;
         font-family: Arial;
         font-size: 14px;
         z-index: 9999;">
         
    <div style="font-weight: bold; margin-bottom: 8px; font-size: 15px;">
        Parking Map Legend
    </div>
    <div style="font-size: 11px; color: #666; margin-bottom: 10px;">
        {check_time.strftime('%I:%M %p on %A')}
    </div>

    <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #ddd;">
        <strong style="font-size: 12px;">Parking Zones:</strong>
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <div style="width: 18px; height: 18px; background-color: #FF0000; margin-right: 8px; border: 1px solid #999;"></div>
        No Parking Now
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <div style="width: 18px; height: 18px; background-color: #FFFF00; margin-right: 8px; border: 1px solid #999;"></div>
        1 Hour Limit
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <div style="width: 18px; height: 18px; background-color: #FFA500; margin-right: 8px; border: 1px solid #999;"></div>
        2 Hour Limit
    </div>

    <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <div style="width: 18px; height: 18px; background-color: #00FF00; margin-right: 8px; border: 1px solid #999;"></div>
        3+ Hours / Unrestricted
    </div>

    <div style="margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px solid #ddd;">
        <strong style="font-size: 12px;">Violation Heatmap:</strong>
    </div>
    <div style="font-size: 11px; color: #666;">
        Red = High violations<br>
        Yellow = Medium violations<br>
        Green = Low violations
    </div>

    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save to the public maps folder
    output_file = "frontend/my-app/public/maps/usf_parking_combined.html"
    m.save(output_file)
    
    # Ensure file is fully written to disk
    import os
    import time
    time.sleep(0.2)
    
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        print(f"✅ Combined map saved to {output_file} ({os.path.getsize(output_file)} bytes)")
    else:
        print(f"⚠️ Warning: File may not be properly saved")
    
    return check_time

# === ROUTES ===

@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/regenerate-map', methods=['POST'])
def regenerate_map():
    """
    Regenerate the parking map with current time data
    """
    try:
        check_time = generate_parking_map()
        return jsonify({
            "success": True,
            "message": "Map regenerated successfully",
            "timestamp": check_time.strftime('%I:%M %p on %A, %B %d, %Y')
        })
    except Exception as e:
        print(f"❌ Error regenerating map: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/regenerate-combined-map', methods=['POST'])
def regenerate_combined_map():
    """
    Regenerate the combined parking map with current time data
    """
    try:
        check_time = generate_combined_map()
        return jsonify({
            "success": True,
            "message": "Combined map regenerated successfully",
            "timestamp": check_time.strftime('%I:%M %p on %A, %B %d, %Y')
        })
    except Exception as e:
        print(f"❌ Error regenerating combined map: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/zones')
def zones():
    """Return real parking zone data from CSV file."""
    print("Serving real parking zones from CSV...")
    
    try:
        features = []
        lat_min, lat_max = 37.774, 37.785
        lon_min, lon_max = -122.460, -122.440
        
        for idx, row in parking_df.iterrows():
            try:
                geom = wkt.loads(row['shape'])
                centroid = geom.centroid
                
                if not (lat_min <= centroid.y <= lat_max and lon_min <= centroid.x <= lon_max):
                    continue
                
                hrs_begin = row.get('HRS_BEGIN', '')
                hrs_end = row.get('HRS_END', '')
                
                hrs_begin = str(int(hrs_begin)) if pd.notna(hrs_begin) and hrs_begin != '' else ''
                hrs_end = str(int(hrs_end)) if pd.notna(hrs_end) and hrs_end != '' else ''
                
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

@app.route('/tickets')
def tickets():
    """Placeholder for ticket data endpoint."""
    print("Serving sample parking tickets...")
    
    points = []
    lat_center = 37.7765
    lon_center = -122.4505
    
    for _ in range(200):
        lat = lat_center + (random.random() - 0.5) * 0.01
        lon = lon_center + (random.random() - 0.5) * 0.01
        points.append([lat, lon])
    
    print(f"✓ Generated {len(points)} sample ticket locations")
    return jsonify(points)

if __name__ == '__main__':
    app.run(debug=True, port=5001)