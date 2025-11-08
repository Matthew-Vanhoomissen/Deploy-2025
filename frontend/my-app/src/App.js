import React, { useState, useEffect } from "react";
import "./App.css";

const App = () => {
  const [openDropdown, setOpenDropdown] = useState(null);
  const [activeTab, setActiveTab] = useState("map"); // default tab is Map

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
    if (tab === "map") {
      setActiveTab("map");
      setOpenDropdown(null);
    } else {
      setOpenDropdown(openDropdown === tab ? null : tab);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo">
            <img src="logo1.png" alt="Logo" />
          </div>
          <h1 className="app-title">Dons Parking Support</h1>
        </div>

        <div className="tab-bar">
          <div className="tab" onClick={() => handleTabClick("map")}>
            Map
          </div>

          <div className="tab" onClick={() => handleTabClick("settings")}>
            Settings
            <div className={`tab-dropdown ${openDropdown === "settings" ? "active" : ""}`}>
              <button onClick={() => alert("Option 1 clicked")}>Option 1</button>
              <button onClick={() => alert("Option 2 clicked")}>Option 2</button>
              <button onClick={() => alert("Option 3 clicked")}>Option 3</button>
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

      <div className="map-container">
        {activeTab === "map" && (
          <iframe
            src="/map.html"
            title="Folium Map"
            width="100%"
            height="100%"
            style={{ border: "none" }}
          />
        )}
      </div>
    </div>
  );
};

export default App;