import React, { useState, useEffect, useRef } from "react";
import { APIProvider, Map } from "@vis.gl/react-google-maps";
import "./App.css";

const App = () => {
  const apiKey = "AIzaSyCQce9x-LQ_oI_lJ1AErnydVretMH-IvAQ"; // Replace with your API key
  const mapId = "445ffbbf47289511332744ba"; // Optional custom map style

  const [openDropdown, setOpenDropdown] = useState(null);
  const mapRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest(".tab")) {
        setOpenDropdown(null);
      }
    };
    window.addEventListener("click", handleClickOutside);
    return () => window.removeEventListener("click", handleClickOutside);
  }, []);

  const handleTabClick = (tab) => {
    setOpenDropdown(openDropdown === tab ? null : tab);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo">
            <img src="/logo1.png" alt="App Logo" />
          </div>
          <h1 className="app-title">Dons Parking Support</h1>
        </div>

        <div className="tab-bar">
          <div className="tab" onClick={() => handleTabClick("map")}>
            Map
            <div className={`tab-dropdown ${openDropdown === "map" ? "active" : ""}`}>
              <button onClick={() => alert("Center Map")}>Center Map</button>
              <button onClick={() => alert("Zoom In")}>Zoom In</button>
              <button onClick={() => alert("Zoom Out")}>Zoom Out</button>
            </div>
          </div>

          <div className="tab" onClick={() => handleTabClick("Filters")}>
            Filters
            <div className={`tab-dropdown ${openDropdown === "Filters" ? "active" : ""}`}>
              <button onClick={() => alert("Option 1 clicked")}>Option 1</button>
              <button onClick={() => alert("Option 2 clicked")}>Option 2</button>
            </div>
          </div>

          <div className="tab" onClick={() => handleTabClick("info")}>
            Info
            <div className={`tab-dropdown ${openDropdown === "info" ? "active" : ""}`}>
              <button onClick={() => alert("About clicked")}>About</button>
              <button onClick={() => alert("Help clicked")}>Help</button>
            </div>
          </div>
        </div>
      </header>

      {/* Map */}
      <div className="map-container" ref={mapRef}>
        <div className="map-wrapper">
          <APIProvider apiKey={apiKey} onLoad={() => console.log("Maps API loaded")}>
            <Map
              defaultZoom={16}
              defaultCenter={{ lat: 37.7749, lng: -122.4521 }}
              mapId={mapId}
              style={{ width: "100%", height: "100%" }}
            />
          </APIProvider>
        </div>
      </div>
    </div>
  );
};

export default App;