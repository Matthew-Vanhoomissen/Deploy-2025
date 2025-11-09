import React, { useState, useEffect } from "react";
import "./App.css";

const App = () => {
  const [openDropdown, setOpenDropdown] = useState(null);
  const [activeTab, setActiveTab] = useState("map");
  const [filters, setFilters] = useState({
    availability: "all",
    priceRange: "all",
    distance: "all",
    parkingType: "all",
    mapView: "standard"
  });
  const [loading, setLoading] = useState(false);

  const handleMapChange = (newView) => {
    setLoading(true); // show loading overlay
    setFilters(prev => ({
      ...prev,
      mapView: newView
    }));
  };

  useEffect(() => {
    const iframe = document.querySelector(".map-container iframe");
    if (iframe) {
      iframe.onload = () => setLoading(false, 2000); // hide loading when map is ready
    }
  }, [filters.mapView]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest(".tab") && !e.target.closest(".filter-modal") && !e.target.closest(".info-modal")) {
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
      setActiveTab(tab);
    }
  };

  const closeModal = () => {
    setOpenDropdown(null);
    setActiveTab("map");
  };

  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
    if (filterType === "mapView") handleMapChange(value);
  };

  const resetFilters = () => {
    setFilters({
      availability: "all",
      priceRange: "all",
      distance: "all",
      parkingType: "all",
      mapView: "standard"
    });
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
            className={`tab ${openDropdown === "filters" ? "active" : ""}`}
            onClick={() => handleTabClick("filters")}
          >
            Filters
          </div>
          <div
            className={`tab ${openDropdown === "info" ? "active" : ""}`}
            onClick={() => handleTabClick("info")}
          >
            Info
          </div>
        </div>
      </header>

      {/* Filter Modal */}
      {openDropdown === "filters" && (
        <>
          <div className="modal-overlay" onClick={closeModal}></div>
          <div className="filter-modal">
            <div className="modal-header">
              <h2>Filter Parking Spots</h2>
              <button className="close-modal" onClick={closeModal}>✕</button>
            </div>
            
            <div className="filter-grid">
              <div className="filter-section">
                <div className="section-title">Map View</div>
                <div className="filter-buttons">
                  <button
                    className={filters.mapView === "standard" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "standard"); }}
                  >
                    🗺️ Standard Map
                  </button>
                  <button
                    className={filters.mapView === "heatmap" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "heatmap"); }}
                  >
                    🔥 Heatmap View
                  </button>
                  <button
                    className={filters.mapView === "streetHours" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "streetHours"); }}
                  >
                    🛣️ Street Parking Hours
                  </button>
                  <button
                    className={filters.mapView === "combinedView" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "combinedView"); }}
                  >
                    🔗 Combined View
                  </button>
                </div>
              </div>

              {/* Availability */}
              <div className="filter-section">
                <div className="section-title">Availability</div>
                <div className="filter-buttons">
                  <button
                    className={filters.availability === "all" ? "selected" : ""}
                    onClick={() => handleFilterChange("availability", "all")}
                  >
                    All Spots
                  </button>
                  <button
                    className={filters.availability === "available" ? "selected" : ""}
                    onClick={() => handleFilterChange("availability", "available")}
                  >
                    Available Only
                  </button>
                  <button
                    className={filters.availability === "occupied" ? "selected" : ""}
                    onClick={() => handleFilterChange("availability", "occupied")}
                  >
                    Occupied
                  </button>
                </div>
              </div>

              {/* Price Range */}
              <div className="filter-section">
                <div className="section-title">Price Range</div>
                <div className="filter-buttons">
                  <button
                    className={filters.priceRange === "all" ? "selected" : ""}
                    onClick={() => handleFilterChange("priceRange", "all")}
                  >
                    All Prices
                  </button>
                  <button
                    className={filters.priceRange === "free" ? "selected" : ""}
                    onClick={() => handleFilterChange("priceRange", "free")}
                  >
                    Free
                  </button>
                  <button
                    className={filters.priceRange === "low" ? "selected" : ""}
                    onClick={() => handleFilterChange("priceRange", "low")}
                  >
                    $ Low ($0-5)
                  </button>
                  <button
                    className={filters.priceRange === "medium" ? "selected" : ""}
                    onClick={() => handleFilterChange("priceRange", "medium")}
                  >
                    $ Medium ($5-15)
                  </button>
                  <button
                    className={filters.priceRange === "high" ? "selected" : ""}
                    onClick={() => handleFilterChange("priceRange", "high")}
                  >
                    $$ High ($15+)
                  </button>
                </div>
              </div>

              {/* Distance */}
              <div className="filter-section">
                <div className="section-title">Distance</div>
                <div className="filter-buttons">
                  <button
                    className={filters.distance === "all" ? "selected" : ""}
                    onClick={() => handleFilterChange("distance", "all")}
                  >
                    Any Distance
                  </button>
                  <button
                    className={filters.distance === "near" ? "selected" : ""}
                    onClick={() => handleFilterChange("distance", "near")}
                  >
                    Within 0.5 mi
                  </button>
                  <button
                    className={filters.distance === "medium" ? "selected" : ""}
                    onClick={() => handleFilterChange("distance", "medium")}
                  >
                    Within 1 mi
                  </button>
                  <button
                    className={filters.distance === "far" ? "selected" : ""}
                    onClick={() => handleFilterChange("distance", "far")}
                  >
                    Within 2 mi
                  </button>
                </div>
              </div>

              {/* Parking Type */}
              <div className="filter-section">
                <div className="section-title">Parking Type</div>
                <div className="filter-buttons">
                  <button
                    className={filters.parkingType === "all" ? "selected" : ""}
                    onClick={() => handleFilterChange("parkingType", "all")}
                  >
                    All Types
                  </button>
                  <button
                    className={filters.parkingType === "garage" ? "selected" : ""}
                    onClick={() => handleFilterChange("parkingType", "garage")}
                  >
                    🏢 Garage
                  </button>
                  <button
                    className={filters.parkingType === "lot" ? "selected" : ""}
                    onClick={() => handleFilterChange("parkingType", "lot")}
                  >
                    🅿️ Parking Lot
                  </button>
                  <button
                    className={filters.parkingType === "street" ? "selected" : ""}
                    onClick={() => handleFilterChange("parkingType", "street")}
                  >
                    🛣️ Street Parking
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button className="reset-button" onClick={resetFilters}>
                Reset All Filters
              </button>
              <button className="apply-button" onClick={closeModal}>
                Apply Filters
              </button>
            </div>
          </div>
        </>
      )}

      {/* Info Modal */}
      {openDropdown === "info" && (
        <>
          <div className="modal-overlay" onClick={closeModal}></div>
          <div className="info-modal">
            <div className="modal-header">
              <h2>Information</h2>
              <button className="close-modal" onClick={closeModal}>✕</button>
            </div>
            <div className="info-content">
              <button className="info-item">About</button>
              <button className="info-item">Help</button>
              <button className="info-item">Contact</button>
            </div>
          </div>
        </>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <div className="loading-text">Loading map...</div>
        </div>
      )}

      {/* Map Background */}
      <div className="map-container">
        <iframe 
          src={
            filters.mapView === "heatmap"
              ? "/maps/usf_parking_heatmap.html"
              : filters.mapView === "streetHours"
                ? "/maps/street_hours_map.html"
                : filters.mapView === "combinedView"
                  ? "/maps/usf_parking_combined.html"
                  : "/maps/Home_Map.html"
          } 
          title="Map" 
          key={filters.mapView}
        />
      </div>
    </div>
  );
};

export default App;