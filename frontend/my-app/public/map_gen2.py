import folium
import folium.plugins

# USF Campus coordinates
USF_CAMPUS = [37.7763, -122.4505]

def create_home_map():
    m = folium.Map(
        location=USF_CAMPUS,
        zoom_start=16,
        tiles='OpenStreetMap'
    )

    # Add Geocoder search box
    folium.plugins.Geocoder(
        collapsed=False,
        position='bottomleft',  # keep bottomleft for leaflet positioning
        placeholder='Search streets, addresses...'
    ).add_to(m)

    # Centered bottom CSS
    custom_css = """
<style>
/* Center geocoder at bottom */
.leaflet-bottom.leaflet-left {
    left: 50% !important;
    bottom: 20px !important;
    transform: translateX(-50%) !important;
    width: 70% !important;
    max-width: 800px !important;
    z-index: 1000 !important;
}

/* Geocoder container */
.leaflet-control-geocoder {
    background: rgba(0,77,64,0.55) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 2rem !important;
    padding: 8px 12px !important;
    display: flex !important;
    align-items: center !important;
}

/* Input field */
.leaflet-control-geocoder-form input {
    flex: 1 !important;
    padding: 8px 12px !important;
    border-radius: 1.2rem !important;
    border: none !important;
    font-size: 1.1rem !important;
    color: #f1f1f1 !important;
    background: rgba(255,255,255,0.2) !important;
    outline: none !important;
}

/* Input placeholder */
.leaflet-control-geocoder-form input::placeholder {
    color: rgba(255,255,255,0.7) !important;
}

/* Icon styling */
.leaflet-control-geocoder-icon {
    all: unset !important;
    width: 24px !important;
    height: 24px !important;
    cursor: pointer !important;
    margin-left: 8px;
    filter: brightness(1.3);
}

/* Dropdown / results popup */
.leaflet-control-geocoder-alternatives {
    max-height: 250px !important;
    overflow-y: auto !important;
    background: rgba(0,77,64,0.95) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 1rem !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
    margin-top: 4px !important;
    padding: 4px 0 !important;
}

/* Dropdown items */
.leaflet-control-geocoder-alternatives li {
    padding: 8px 14px !important;
    color: #ffffff !important;  /* <-- set to white */
    font-size: 1rem !important;
    border-radius: 0.5rem !important;
    transition: background 0.2s ease !important;
}

.leaflet-control-geocoder-alternatives li:hover {
    background: rgba(76,175,80,0.3) !important;
    cursor: pointer !important;
}

/* Scrollbar */
.leaflet-control-geocoder-alternatives::-webkit-scrollbar {
    width: 6px !important;
}

.leaflet-control-geocoder-alternatives::-webkit-scrollbar-thumb {
    background: rgba(76,175,80,0.6) !important;
    border-radius: 3px !important;
}
</style>
    """

    # Add CSS to map
    m.get_root().html.add_child(folium.Element(custom_css))

    # Save map
    m.save('Home_Map.html')
    print("✅ Home_Map.html created successfully with centered bottom search bar!")

if __name__ == "__main__":
    print("Generating USF Parking Home Map...")
    create_home_map()