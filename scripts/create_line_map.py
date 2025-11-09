import folium
import folium.plugins
import requests
from datetime import datetime

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

# Create base map centered on USF
usf_center = [37.7765, -122.4505]
m = folium.Map(location=usf_center, zoom_start=16)

# ✅ ADD SEARCH BAR (no edits to your original logic)
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

# You can change this to test different times
check_time = datetime.now()
print(f"🕐 Checking parking availability for: {check_time.strftime('%A, %B %d, %Y at %I:%M %p')}")

try:
    response = requests.get("http://127.0.0.1:5001/zones")
    data = response.json()
    
    print(f"📍 Loaded {len(data.get('features', []))} parking zones")
    
    allowed_count = 0
    restricted_count = 0
    geometry_errors = 0
    
    for idx, feature in enumerate(data.get('features', [])):
        try:
            props = feature['properties']
            geom = feature['geometry']
            coords = geom['coordinates']
            
            if idx == 0:
                print(f"\n🔍 DEBUG - First feature:")
                print(f"   Geometry type: {geom['type']}")
                print(f"   Coordinates sample: {coords[0] if coords else 'empty'}")
                print(f"   Properties: {props}")
            
            is_allowed, hours = is_parking_allowed_now(props, check_time)
            
            if is_allowed:
                allowed_count += 1
            else:
                restricted_count += 1
            
            color = get_color_by_availability(is_allowed, hours)
            
            if geom['type'] == 'LineString':
                line_coords = [[coord[1], coord[0]] for coord in coords]
            elif geom['type'] == 'MultiLineString':
                line_coords = []
                for line in coords:
                    line_coords.extend([[coord[1], coord[0]] for coord in line])
            else:
                print(f"⚠️  Skipping unsupported geometry type: {geom['type']}")
                geometry_errors += 1
                continue
            
            if not line_coords or len(line_coords) < 2:
                print(f"⚠️  Skipping feature {idx}: insufficient coordinates")
                geometry_errors += 1
                continue
        except Exception as e: 
            print(f"Error with adding line {e}")

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
    
except Exception as e:
    print(f"❌ Error loading parking zones: {e}")
    print("Make sure your Flask server is running on http://127.0.0.1:5001")

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

output_file = "usf_parking_current_status.html"
m.save(output_file)
print(f"\n✅ Map saved to {output_file}")

import webbrowser
webbrowser.open(output_file)
