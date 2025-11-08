import React, { useState } from "react";
import { APIProvider, Map } from "@vis.gl/react-google-maps";

const App = () => {
  const apiKey = ""; 
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
      
      <div style={{ height: "500px" }}>
        <APIProvider apiKey={apiKey} onLoad={() => console.log("Maps API loaded")}>
          <Map
            defaultZoom={16}
            defaultCenter={{ lat: 37.7749, lng: -122.4521 }}
            mapId={mapId}
            style={{ width: "100%", height: "100%" }}
          />
        </APIProvider>
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
            value={filters.permitType}
            onChange={(e) => setFilters({...filters, permitType: e.target.value})}
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "4px",
              border: "1px solid #ccc",
              fontSize: "1rem"
            }}
          >
            <option value="all">All Permits</option>
            <option value="resident">Resident</option>
            <option value="commuter">Commuter</option>
            <option value="visitor">Visitor</option>
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