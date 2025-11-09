import folium
from folium.plugins import HeatMap
import pandas as pd
import webbrowser
from sklearn.cluster import DBSCAN
import numpy as np
from math import radians, sin, cos, sqrt, atan2

# Load your filtered ticket data
df = pd.read_csv("../data/tickets_with_coords.csv")  

# Keep only rows with valid coordinates
df = df[(df["latitude"].notna()) & (df["longitude"].notna())]
df = df[(df["latitude"] != 0) & (df["longitude"] != 0)]

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




# Center of USF
usf_center = [37.7763, -122.4505]

# Filter to within 1 mile of USF center
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two lat/lon points"""
    R = 3959  # Earth's radius in miles
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

# Calculate distance and filter
df['distance_miles'] = df.apply(
    lambda row: haversine_distance(usf_center[0], usf_center[1], row['latitude'], row['longitude']),
    axis=1
)
df = df[df['distance_miles'] <= 1.0]

print(f"🔍 Filtered to tickets within 1 mile: {len(df)} tickets")

# Create base map
m = folium.Map(location=usf_center, zoom_start=16, tiles="OpenStreetMap")

# ✅ Add Search Bar
folium.plugins.Geocoder(
    collapsed=False,
    position='bottomleft',
    placeholder='Search streets, addresses...'
).add_to(m)

# ✅ Add custom CSS styling for search bar
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
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    border: none !important;
    padding: 10px 18px !important;
    width: 100% !important;
    height: 60px !important;
    display: flex !important;
    align-items: center !important;
}
.leaflet-control-geocoder-form {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
}
.leaflet-control-geocoder-form input {
    flex: 1 !important;
    width: 100% !important;
    background: rgba(255, 255, 255, 0.25) !important;
    border: none !important;
    border-radius: 1.5rem !important;
    padding: 10px 14px !important;
    font-size: 1.1rem !important;
    color: #f1f1f1 !important;
    outline: none !important;
}
.leaflet-control-geocoder-form input::placeholder {
    color: rgba(255, 255, 255, 0.85) !important;
}
.leaflet-control-geocoder-icon {
    all: unset !important;
    width: 24px !important;
    height: 24px !important;
    filter: brightness(1.4);
}
.leaflet-control-geocoder-alternatives {
    max-height: 150px !important;
    overflow-y: auto !important;
    background: rgba(0, 77, 64, 0.85) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 1rem !important;
    margin-top: 8px !important;
    box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4) !important;
}
.leaflet-control-geocoder-alternatives li {
    padding: 8px 14px !important;
    font-size: 1rem !important;
    color: rgba(255, 255, 255, 0.9) !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 0.5rem !important;
    transition: background 0.2s ease !important;
}
.leaflet-control-geocoder-alternatives li:hover {
    background: rgba(76, 175, 80, 0.25) !important;
    cursor: pointer !important;
}
</style>
"""
m.get_root().html.add_child(folium.Element(custom_css))

# Prepare data for heatmap
heat_data = [[row['latitude'], row['longitude']] for idx, row in df.iterrows()]

# Add heatmap layer
HeatMap(
    heat_data,
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

# Find clusters using DBSCAN (groups nearby points)
coords = df[['latitude', 'longitude']].values
# eps controls how close points need to be (in degrees, ~0.0001 ≈ 11 meters)
clustering = DBSCAN(eps=0.0002, min_samples=10).fit(coords)
df['cluster'] = clustering.labels_

# Add clickable markers for significant clusters (10+ violations)
cluster_counts = df[df['cluster'] != -1].groupby('cluster').size()
significant_clusters = cluster_counts[cluster_counts >= 15]

print(f"\n📊 Found {len(significant_clusters)} clusters with 10+ violations:")

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

# Save the heatmap
m.save("usf_parking_heatmap1.html")
print("\n✅ Heatmap saved: usf_parking_heatmap.html")
print(f"📍 Total tickets mapped: {len(heat_data)}")

folium.Html("usf_parking_current_status.html").add_to(m)
m.save("usf_combined.html")
webbrowser.open("usf_combined.html")