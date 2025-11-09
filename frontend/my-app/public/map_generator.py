import folium

# Create the map
m = folium.Map(location=[37.7749, -122.4521], zoom_start=16)
folium.Marker([37.7749, -122.4521], popup="Dons Parking").add_to(m)

# Save inside the React public folder
m.save("map.html")  # if you run this from 'public' folder
# OR
m.save("../public/map.html")  # if you run this from the project root