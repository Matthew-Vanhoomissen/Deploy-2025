/* global google */
import React, { useState, useEffect } from "react";
import { APIProvider, Map, useMap } from "@vis.gl/react-google-maps";

// Helper function to determine parking hours
const getMaxHours = (properties) => {
  if (properties.max_hours !== undefined) {
    return properties.max_hours;
  }
  
  const begin = Number(properties.hrs_begin || properties.HRS_BEGIN);
  const end = Number(properties.hrs_end || properties.HRS_END);
  
  if (!isNaN(begin) && !isNaN(end) && begin > 0 && end > 0) {
    const beginHours = Math.floor(begin / 100) + (begin % 100) / 60;
    const endHours = Math.floor(end / 100) + (end % 100) / 60;
    return endHours - beginHours > 0 ? endHours - beginHours : 0;
  }
  
  const rule = ((properties.regulation || properties.REGULATION) || '').toUpperCase();
  if (rule.includes('NO PARKING') || rule.includes('TOW-AWAY') || rule.includes('NO STOPPING')) {
    return 0;
  }
  
  if (rule.includes('1 HR') || rule.includes('1HR') || rule.includes('1 HOUR')) return 1;
  if (rule.includes('2 HR') || rule.includes('2HR') || rule.includes('2 HOUR')) return 2;
  if (rule.includes('3 HR') || rule.includes('3HR') || rule.includes('3 HOUR')) return 3;
  if (rule.includes('4 HR') || rule.includes('4HR') || rule.includes('4 HOUR')) return 4;
  
  return null;
};

// Helper function to get color based on hours
const getColorByHours = (hours) => {
  if (hours === null) return "#808080";
  if (hours <= 0) return "#FF0000";
  else if (hours === 1) return "#FFFF00";
  else if (hours === 2) return "#FFA500";
  else return "#00FF00";
};

// Component to add parking zones and heatmap to the map
const ParkingOverlay = () => {
  const map = useMap();
  const [parkingZones, setParkingZones] = useState([]);
  const [ticketPoints, setTicketPoints] = useState([]);

  useEffect(() => {
    if (!map) return;

    // Fetch parking zones
    fetch("http://127.0.0.1:5001/zones")
      .then(res => res.json())
      .then(data => {
        console.log("Loaded zones:", data.features?.length);
        if (data.features && data.features.length > 0) {
          setParkingZones(data.features);
        }
      })
      .catch(err => console.error("Error loading tickets:", err));
  }, [map]);

  useEffect(() => {
    if (!map || parkingZones.length === 0) return;

    // Add parking zone polylines to map
    const polylines = parkingZones.map((feature) => {
      const hours = getMaxHours(feature.properties);
      const color = getColorByHours(hours);
      
      // Convert GeoJSON coordinates to Google Maps LatLng format
      const path = feature.geometry.coordinates.map((coord) => ({
        lat: coord[1],
        lng: coord[0]
      }));

      const polyline = new google.maps.Polyline({
        path: path,
        strokeColor: color,
        strokeOpacity: 1.0,
        strokeWeight: 6,
        map: map
      });

      // Add click listener for info window
      const infoWindow = new google.maps.InfoWindow();
      polyline.addListener('click', (event) => {
        const props = feature.properties;
        infoWindow.setContent(`
          <div style="padding: 8px;">
            <strong>Regulation:</strong> ${props.regulation || props.REGULATION || 'N/A'}<br>
            <strong>Days:</strong> ${props.days || props.DAYS || 'N/A'}<br>
            <strong>Hours:</strong> ${props.hrs_begin || props.HRS_BEGIN || 'N/A'} - ${props.hrs_end || props.HRS_END || 'N/A'}<br>
            <strong>Max Parking:</strong> ${hours !== null ? hours + ' hours' : 'Unknown'}
          </div>
        `);
        infoWindow.setPosition(event.latLng);
        infoWindow.open(map);
      });

      return polyline;
    });

    // Cleanup function
    return () => {
      polylines.forEach((polyline) => polyline.setMap(null));
    };
  }, [map, parkingZones]);

    return null;
};

  

// Legend component
const Legend = () => (
  <div style={{
    position: "absolute",
    bottom: "20px",
    right: "20px",
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    padding: "15px",
    borderRadius: "8px",
    boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
    fontFamily: "Arial, sans-serif",
    fontSize: "14px",
    zIndex: 1000
  }}>
    <div style={{ fontWeight: "bold", marginBottom: "8px", fontSize: "15px" }}>
      Parking Duration
    </div>
    <div style={{ display: "flex", alignItems: "center", marginBottom: "5px" }}>
      <div style={{ width: "18px", height: "18px", backgroundColor: "#FF0000", marginRight: "8px", border: "1px solid #999" }}></div>
      No Parking
    </div>
    <div style={{ display: "flex", alignItems: "center", marginBottom: "5px" }}>
      <div style={{ width: "18px", height: "18px", backgroundColor: "#FFFF00", marginRight: "8px", border: "1px solid #999" }}></div>
      1 Hour
    </div>
    <div style={{ display: "flex", alignItems: "center", marginBottom: "5px" }}>
      <div style={{ width: "18px", height: "18px", backgroundColor: "#FFA500", marginRight: "8px", border: "1px solid #999" }}></div>
      2 Hours
    </div>
    <div style={{ display: "flex", alignItems: "center", marginBottom: "5px" }}>
      <div style={{ width: "18px", height: "18px", backgroundColor: "#00FF00", marginRight: "8px", border: "1px solid #999" }}></div>
      3+ Hours
    </div>
    <div style={{ display: "flex", alignItems: "center" }}>
      <div style={{ width: "18px", height: "18px", backgroundColor: "#808080", marginRight: "8px", border: "1px solid #999" }}></div>
      Unknown
    </div>
  </div>
);

const App = () => {
  const apiKey = "AIzaSyCQce9x-LQ_oI_lJ1AErnydVretMH-IvAQ"; 
  const mapId = "445ffbbf47289511332744ba";
  
  const [filters, setFilters] = useState({
    Day_of_the_Week: "all",
    availability: "all"
  });

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          backgroundColor: "#004d40",
          color: "#fff",
          padding: "1rem",
          textAlign: "center",
          fontSize: "1.5rem",
          fontWeight: "600"
        }}
      >
        Dons Parking Support
      </header>
      
      <div style={{ height: "500px", position: "relative" }}>
        <APIProvider 
          apiKey={apiKey} 
          onLoad={() => console.log("Maps API loaded")}
          libraries={['visualization']}
        >
          <Map
            defaultZoom={16}
            defaultCenter={{ lat: 37.7765, lng: -122.4505 }}
            mapId={mapId}
            style={{ width: "100%", height: "100%" }}
          >
            <ParkingOverlay />
          </Map>
        </APIProvider>
        <Legend />
      </div>
      
      <div style={{ 
        padding: "2rem",
        backgroundColor: "#fff",
        flex: 1,
        overflowY: "auto"
      }}>
        <h2 style={{ marginTop: 0, marginBottom: "1.5rem", color: "#004d40" }}>
          Filters
        </h2>
        
        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ 
            display: "block", 
            marginBottom: "0.5rem",
            fontWeight: "500",
            color: "#333"
          }}>
            Day of the Week:
          </label>
          <select 
            value={filters.Day_of_the_Week}
            onChange={(e) => setFilters({...filters, Day_of_the_Week: e.target.value})}
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "4px",
              border: "1px solid #ccc",
              fontSize: "1rem"
            }}
          >
            <option value="all">All Days</option>
            <option value="monday">Monday</option>
            <option value="tuesday">Tuesday</option>
            <option value="wednesday">Wednesday</option>
            <option value="thursday">Thursday</option>
            <option value="friday">Friday</option>
            <option value="saturday">Saturday</option>
            <option value="sunday">Sunday</option>
          </select>
        </div>
        
        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ 
            display: "block", 
            marginBottom: "0.5rem",
            fontWeight: "500",
            color: "#333"
          }}>
            Availability:
          </label>
          <select 
            value={filters.availability}
            onChange={(e) => setFilters({...filters, availability: e.target.value})}
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "4px",
              border: "1px solid #ccc",
              fontSize: "1rem"
            }}
          >
            <option value="all">All Lots</option>
            <option value="available">Available Now</option>
            <option value="limited">Limited Spots</option>
            <option value="full">Full</option>
          </select>
        </div>
        
        <button
          style={{
            width: "100%",
            padding: "0.75rem",
            backgroundColor: "#004d40",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            fontSize: "1rem",
            fontWeight: "500",
            cursor: "pointer"
          }}
          onClick={() => console.log("Filters applied:", filters)}
        >
          Apply Filters
        </button>
      </div>
    </div>
  );
};

export default App;