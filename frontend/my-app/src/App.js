import React, { useState, useEffect } from "react";
import "./App.css";

const App = () => {
  const [openDropdown, setOpenDropdown] = useState(null);
  const [activeTab, setActiveTab] = useState("map");

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
      {/* Floating Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo">
            <img src="/logo1.png" alt="Logo" />
          </div>
          <h1 className="app-title">Dons Parking Support</h1>
        </div>

        <div className="tab-bar">
          <div
            className={`tab ${activeTab === "map" ? "active" : ""}`}
            onClick={() => handleTabClick("map")}
          >
            Map
          </div>

          <div
            className={`tab ${openDropdown === "settings" ? "active" : ""}`}
            onClick={() => handleTabClick("settings")}
          >
            Settings
            <div className={`tab-dropdown ${openDropdown === "settings" ? "active" : ""}`}>
              <button>Option 1</button>
              <button>Option 2</button>
              <button>Option 3</button>
            </div>
          </div>

          <div
            className={`tab ${openDropdown === "info" ? "active" : ""}`}
            onClick={() => handleTabClick("info")}
          >
            Info
            <div className={`tab-dropdown ${openDropdown === "info" ? "active" : ""}`}>
              <button>About</button>
              <button>Help</button>
            </div>
          </div>
        </div>
      </header>

      {/* Map Background */}
      <div className="map-container">
        {activeTab === "map" && <iframe src="/map.html" title="Folium Map" />}
      </div>
    </div>
  );
};

export default App;