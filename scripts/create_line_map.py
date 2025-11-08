import folium
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
    """
    Check if parking is allowed at the given time
    Returns: (is_allowed: bool, hours_available: float or None)
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Get day of week (0 = Monday, 6 = Sunday)
    current_day = check_time.weekday()
    day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
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
        # Handle common day formats (with or without hyphens/underscores)
        days_normalized = days.replace('_', '-')
        if 'MON-FRI' in days_normalized or 'WEEKDAYS' in days_normalized:
            if current_day >= 5:  # Saturday or Sunday
                return (True, None)  # No restriction on weekends
        elif 'SAT-SUN' in days_normalized or 'WEEKENDS' in days_normalized:
            if current_day < 5:  # Monday-Friday
                return (True, None)  # No restriction on weekdays
        elif current_day_name not in days:
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


# Create base map centered on USF
usf_center = [37.7765, -122.4505]
m = folium.Map(location=usf_center, zoom_start=16)

# You can change this to test different times
# For example: datetime(2024, 11, 8, 14, 30) for Friday at 2:30 PM
check_time = datetime.now()
print(f"🕐 Checking parking availability for: {check_time.strftime('%A, %B %d, %Y at %I:%M %p')}")

# Fetch parking zones from your local server
try:
    response = requests.get("http://127.0.0.1:5001/zones")
    data = response.json()
    
    print(f"📍 Loaded {len(data.get('features', []))} parking zones")
    
    allowed_count = 0
    restricted_count = 0
    
    # Add each parking zone as a polyline
    for feature in data.get('features', []):
        props = feature['properties']
        coords = feature['geometry']['coordinates']
        
        # Check if parking is allowed NOW
        is_allowed, hours = is_parking_allowed_now(props, check_time)
        
        if is_allowed:
            allowed_count += 1
        else:
            restricted_count += 1
        
        # Get color based on current availability
        color = get_color_by_availability(is_allowed, hours)
        
        # Convert coordinates to Folium format [lat, lon]
        line_coords = [[coord[1], coord[0]] for coord in coords]
        
        # Create popup content
        status = "✅ PARKING ALLOWED" if is_allowed else "🚫 NO PARKING NOW"
        popup_html = f"""
        <div style="font-family: Arial; width: 280px;">
            <h4 style="margin: 0 0 10px 0; color: {'#00695c' if is_allowed else '#d32f2f'};">{status}</h4>
            <p style="margin: 5px 0;"><strong>Regulation:</strong> {props.get('regulation') or props.get('REGULATION') or 'N/A'}</p>
            <p style="margin: 5px 0;"><strong>Days:</strong> {props.get('days') or props.get('DAYS') or 'N/A'}</p>
            <p style="margin: 5px 0;"><strong>Hours:</strong> {props.get('hrs_begin') or props.get('HRS_BEGIN') or 'N/A'} - {props.get('hrs_end') or props.get('HRS_END') or 'N/A'}</p>
            <p style="margin: 5px 0;"><strong>Current Status:</strong> {f"{hours} hour limit" if hours and is_allowed else "No parking" if not is_allowed else "Unrestricted"}</p>
            <p style="margin: 5px 0; font-size: 11px; color: #666;"><em>As of {check_time.strftime('%I:%M %p')}</em></p>
        </div>
        """
        
        # Add polyline to map
        folium.PolyLine(
            locations=line_coords,
            color=color,
            weight=6,
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

# Add updated legend
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

# Save map
output_file = "usf_parking_current_status.html"
m.save(output_file)
print(f"\n✅ Map saved to {output_file}")

# Open in browser
import webbrowser
webbrowser.open(output_file)