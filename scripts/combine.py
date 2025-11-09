import folium
from folium.plugins import HeatMap
import pandas as pd
import requests
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import webbrowser
from sklearn.cluster import DBSCAN
import numpy as np

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two lat/lon points"""
    R = 3959  # Earth's radius in miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

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
    """
    Check if parking is allowed at the given time
    Returns: (is_allowed: bool, hours_available: float or None)
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Get day of week (0 = Monday, 6 = Sunday)
    current_day = check_time.weekday()
    day_names = ['M', 'TU', 'W', 'TH', 'F', 'SA', 'SU']  # Short format used in real data
    current_day_name = day_names[current_day]
    
    # Get current time as HHMM (e.g., 1430 for 2:30 PM)
    current_time_int = check_time.hour * 100 + check_time.minute
    
    # Get zone properties
    days = str(properties.get('days') or properties.get('DAYS') or '').upper()
    begin = properties.get('hrs_begin') or properties.get('HRS_BEGIN')
    end = properties.get('hrs_end') or properties.get('HRS_END')
    regulation = str(properties.get('regulation') or properties.get('REGULATION') or '').upper()
    
    # Check if today is in the allowed days
    if days:
        # Handle common day formats
        # Real data uses "M-F", "M-SA", "SU", etc.
        if 'M-F' in days:  # Monday to Friday
            if current_day >= 5:  # Saturday or Sunday
                return (True, None)  # No restriction on weekends
        elif 'M-SA' in days:  # Monday to Saturday
            if current_day == 6:  # Sunday only
                return (True, None)  # No restriction on Sunday
        elif 'SA-SU' in days or days == 'SA' or days == 'SU':  # Weekend only
            if current_day < 5:  # Monday-Friday
                return (True, None)  # No restriction on weekdays
        # Check if current day is explicitly listed
        elif current_day_name not in days and 'DAILY' not in days:
            return (True, None)  # Not restricted on this day
    
    # Check if current time is within restriction hours
    if begin and end:
        try:
            begin_int = int(begin)
            end_int = int(end)
            
            # If current time is outside restriction hours, parking is allowed
            if current_time_int < begin_int or current_time_int > end_int:
                return (True, None)  # Outside restricted hours
            else:
                # Within restricted hours - check what type of restriction
                if 'NO PARKING' in regulation or 'TOW-AWAY' in regulation:
                    return (False, 0)  # No parking allowed
                else:
                    # Time-limited parking
                    hours = get_max_hours(properties)
                    return (True, hours)  # Parking allowed with time limit
        except (ValueError, TypeError):
            pass
    
    # Default: check regulation
    if 'NO PARKING' in regulation or 'TOW-AWAY' in regulation:
        return (False, 0)
    
    hours = get_max_hours(properties)
    return (True, hours)

def get_color_by_availability(is_allowed, hours):
    """Get color based on whether parking is currently allowed"""
    if not is_allowed:
        return "#FF0000"  # Red - No parking allowed NOW
    if hours is None:
        return "#00FF00"  # Green - Unrestricted parking
    if hours <= 0:
        return "#FF0000"  # Red - No parking
    elif hours == 1:
        return "#FFFF00"  # Yellow - 1 Hour
    elif hours == 2:
        return "#FFA500"  # Orange - 2 Hours
    else:
        return "#00FF00"  # Green - 3+ Hours

# ============================================================================
# CREATE MAP
# ============================================================================

usf_center = [37.7765, -122.4505]
check_time = datetime.now()

print(f"🗺️  Creating combined parking map...")
print(f"🕐 Time: {check_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n")

# Create base map
m = folium.Map(location=usf_center, zoom_start=16)

# ============================================================================
# ADD SEARCH BAR
# ============================================================================

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

# ============================================================================
# LAYER 2: PARKING ZONE REGULATIONS (UPDATED)
# ============================================================================

print("\n📍 Loading parking zones...")
try:
    response = requests.get("http://127.0.0.1:5001/zones")
    data = response.json()
    
    print(f"📍 Loaded {len(data.get('features', []))} parking zones")
    
    allowed_count = 0
    restricted_count = 0
    geometry_errors = 0
    
    # Add each parking zone as a polyline
    for idx, feature in enumerate(data.get('features', [])):
        try:
            props = feature['properties']
            geom = feature['geometry']
            coords = geom['coordinates']
            
            # Debug first feature
            if idx == 0:
                print(f"\n🔍 DEBUG - First feature:")
                print(f"   Geometry type: {geom['type']}")
                print(f"   Coordinates sample: {coords[0] if coords else 'empty'}")
                print(f"   Properties: {props}")
            
            # Check if parking is allowed NOW
            is_allowed, hours = is_parking_allowed_now(props, check_time)
            
            if is_allowed:
                allowed_count += 1
            else:
                restricted_count += 1
            
            # Get color based on current availability
            color = get_color_by_availability(is_allowed, hours)
            
            # Convert coordinates to Folium format [lat, lon]
            # Handle both LineString and MultiLineString geometries
            if geom['type'] == 'LineString':
                line_coords = [[coord[1], coord[0]] for coord in coords]
            elif geom['type'] == 'MultiLineString':
                # Flatten MultiLineString to single list of coordinates
                line_coords = []
                for line in coords:
                    line_coords.extend([[coord[1], coord[0]] for coord in line])
            else:
                print(f"⚠️  Skipping unsupported geometry type: {geom['type']}")
                geometry_errors += 1
                continue
            
            # Verify we have valid coordinates
            if not line_coords or len(line_coords) < 2:
                print(f"⚠️  Skipping feature {idx}: insufficient coordinates")
                geometry_errors += 1
                continue
                
        except Exception as e: 
            print(f"Error with adding line {e}")
            geometry_errors += 1
            continue

        # Create popup content with additional real data fields
        status = "✅ PARKING ALLOWED" if is_allowed else "🚫 NO PARKING NOW"
        exceptions = props.get('exceptions', '')
        popup_html = f"""
        <div style="font-family: Arial; width: 300px;">
            <h4 style="margin: 0 0 10px 0; color: {'#00695c' if is_allowed else '#d32f2f'};">{status}</h4>
            <p style="margin: 5px 0;"><strong>Regulation:</strong> {props.get('regulation', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Days:</strong> {props.get('days', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Hours:</strong> {props.get('from_time', 'N/A')} - {props.get('to_time', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Current Status:</strong> {f"{hours} hour limit" if hours and is_allowed else "No parking" if not is_allowed else "Unrestricted"}</p>
            {f'<p style="margin: 5px 0; font-size: 11px; color: #0066cc;"><strong>Note:</strong> {exceptions}</p>' if exceptions and exceptions != 'N/A' else ''}
            <p style="margin: 5px 0; font-size: 11px; color: #666;"><em>As of {check_time.strftime('%I:%M %p')}</em></p>
        </div>
        """
        
        # Add polyline to map
        folium.PolyLine(
            locations=line_coords,
            color=color,
            weight=4,
            opacity=1.0,
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{'✅ Available' if is_allowed else '🚫 No parking'}: {hours}hr" if hours else "Click for details"
        ).add_to(m)
    
    print(f"✅ Parking zones processed:")
    print(f"   • {allowed_count} zones allow parking now")
    print(f"   • {restricted_count} zones are currently restricted")
    if geometry_errors > 0:
        print(f"   • {geometry_errors} zones skipped due to geometry errors")
    
except Exception as e:
    print(f"❌ Error loading parking zones: {e}")
    print("Make sure your Flask server is running on http://127.0.0.1:5001")

# ============================================================================
# LAYER 1: PARKING VIOLATION HEATMAP
# ============================================================================

print("\n📊 Loading parking ticket data...")
try:
    df = pd.read_csv("../data/tickets_with_coords.csv")
    df = df[(df["latitude"].notna()) & (df["longitude"].notna())]
    df = df[(df["latitude"] != 0) & (df["longitude"] != 0)]

    # Rename terms 
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
    
    # Filter to within 1 mile
    df['distance_miles'] = df.apply(
        lambda row: haversine_distance(usf_center[0], usf_center[1], 
                                      row['latitude'], row['longitude']),
        axis=1
    )
    df = df[df['distance_miles'] <= 1.0]
    
    heat_data = [[row['latitude'], row['longitude']] for idx, row in df.iterrows()]
    
    # Add heatmap layer
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

    # Find clusters using DBSCAN (groups nearby points)
    coords = df[['latitude', 'longitude']].values
    # eps controls how close points need to be (in degrees, ~0.0001 ≈ 11 meters)
    clustering = DBSCAN(eps=0.0002, min_samples=10).fit(coords)
    df['cluster'] = clustering.labels_

    # Add clickable markers for significant clusters (15+ violations)
    cluster_counts = df[df['cluster'] != -1].groupby('cluster').size()
    significant_clusters = cluster_counts[cluster_counts >= 15]

    print(f"\n📊 Found {len(significant_clusters)} clusters with 15+ violations:")

    for cluster_id in significant_clusters.index:
        cluster_data = df[df['cluster'] == cluster_id]
        count = len(cluster_data)
        
        # Get cluster center
        center_lat = cluster_data['latitude'].mean()
        center_lon = cluster_data['longitude'].mean()
        
        # Get most common violation types in this cluster
        top_violations = cluster_data['violation_desc'].value_counts().head(3)
        
        # Create popup content
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
        
        # Add clickable marker
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
        
        print(f"  • Cluster #{cluster_id}: {count} violations at ({center_lat:.4f}, {center_lon:.4f})")
        print(f"    Top violation: {top_violations.index[0]}")
    
except Exception as e:
    print(f"⚠️  Could not load ticket data: {e}")

# ============================================================================
# ADD LEGEND
# ============================================================================

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

# ============================================================================
# SAVE AND OPEN
# ============================================================================

output_file = "usf_parking_combined.html"
m.save(output_file)
print(f"\n✅ Combined map saved to {output_file}")

webbrowser.open(output_file)