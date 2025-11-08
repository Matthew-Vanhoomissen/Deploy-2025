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

    #MOST IMPORTANT PART: Customize Geocoder appearance

    # Add Geocoder search box
    folium.plugins.Geocoder(
        collapsed=False,
        position='bottomleft',
        placeholder='Search streets, addresses...'
    ).add_to(m)

    custom_css = """
    <style>
    /* Center at bottom */
    .leaflet-bottom.leaflet-left {
        left: 50% !important;
        transform: translateX(-50%) !important;
        bottom: 30px !important;
        z-index: 1000 !important;
        width: 70% !important;
        max-width: 900px !important;
    }

    /* Outer container */
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
        justify-content: flex-start !important;
    }

    /* Force inner form to fill entire container */
    .leaflet-control-geocoder-form {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
    }

    /* Input field full width */
    .leaflet-control-geocoder-form input {
        flex: 1 !important;
        width: 100% !important;
        min-width: 0 !important;
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
        font-weight: 400 !important;
    }

    /* Icon back to default style (no circle, inline) */
    .leaflet-control-geocoder-icon {
        all: unset !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 24px !important;
        height: 24px !important;
        cursor: pointer !important;
        filter: brightness(1.4);
    }

    /* Dropdown styling */
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

    /* Scrollbar for dropdown */
    .leaflet-control-geocoder-alternatives::-webkit-scrollbar {
        width: 6px !important;
    }
    .leaflet-control-geocoder-alternatives::-webkit-scrollbar-thumb {
        background: rgba(76, 175, 80, 0.6) !important;
        border-radius: 3px !important;
    }
</style>

    """

    m.get_root().html.add_child(folium.Element(custom_css))
    m.save('Home_Map3.html')
    print("✅ Home_Map3.html created successfully!")
    print("✓ Icon restored to normal (no circle)")
    print("✓ Search input centered properly and aligned left")
    print("✓ Dropdown limited to 2–3 results with scroll")

if __name__ == "__main__":
    print("Generating USF Parking Home Map...")
    create_home_map()
