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
  const [regenerating, setRegenerating] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [lastUpdateCombined, setLastUpdateCombined] = useState(null);
  const [mapKey, setMapKey] = useState(Date.now());
// Risk Check States
  const [riskResult, setRiskResult] = useState(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState(null);

  const handleMapChange = (newView) => {
    setLoading(true);
    setFilters(prev => ({
      ...prev,
      mapView: newView
    }));
    setMapKey(Date.now());
  };

  const regenerateMap = async () => {
    setRegenerating(true);
    try {
      const response = await fetch('http://127.0.0.1:5001/api/regenerate-map', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        console.log('✅ Map regenerated:', data.timestamp);
        setLastUpdate(data.timestamp);
        
        setTimeout(() => {
          setMapKey(Date.now());
          
          setTimeout(() => {
            setRegenerating(false);
          }, 1500);
        }, 1000);
      } else {
        console.error('❌ Failed to regenerate map:', data.error);
        setRegenerating(false);
      }
    } catch (error) {
      console.error('❌ Error calling regenerate API:', error);
      setRegenerating(false);
    }
  };

  const regenerateCombinedMap = async () => {
    setRegenerating(true);
    try {
      const response = await fetch('http://127.0.0.1:5001/api/regenerate-combined-map', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        console.log('✅ Combined map regenerated:', data.timestamp);
        setLastUpdateCombined(data.timestamp);
        
        setTimeout(() => {
          setMapKey(Date.now());
          
          setTimeout(() => {
            setRegenerating(false);
          }, 1500);
        }, 1000);
      } else {
        console.error('❌ Failed to regenerate combined map:', data.error);
        setRegenerating(false);
      }
    } catch (error) {
      console.error('❌ Error calling regenerate combined API:', error);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    const iframe = document.querySelector(".map-container iframe");
    if (iframe) {
      iframe.onload = () => setTimeout(() => setLoading(false), 500);
    }
  }, [filters.mapView, mapKey]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest(".tab") && !e.target.closest(".filter-modal") && !e.target.closest(".info-modal") && !e.target.closest(".risk-modal")) {
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
    if (filterType === "mapView") handleMapChange(value);
    else setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const resetFilters = () => {
    setFilters({
      availability: "all",
      priceRange: "all",
      distance: "all",
      parkingType: "all",
      mapView: "standard"
    });
    handleMapChange("standard");
  };

  const handleLogoClick = () => {
  setFilters(prev => ({
    ...prev,
    mapView: "standard" // Reset to standard map
  }));
  setMapKey(Date.now()); // Force iframe reload
  setActiveTab("map");   // Close any open dropdowns
  setOpenDropdown(null);
};

  // Risk Check API call
  const handleRiskCheck = async () => {
    const addressInput = document.getElementById("risk-address").value.trim();
    if (!addressInput) {
      setRiskError("Please enter a street name");
      return;
    }

    setRiskLoading(true);
    setRiskError(null);
    setRiskResult(null);

    try {
      const response = await fetch(
        `http://localhost:5001/zone-info/${encodeURIComponent(addressInput)}`
      );
      const data = await response.json();

      if (!response.ok) {
        setRiskError(data.error || "Error fetching risk data");
      } else {
        setRiskResult(data);
      }
    } catch (err) {
      setRiskError("Server error: " + err.message);
    } finally {
      setRiskLoading(false);
    }
  };


  const defaultMap = "/maps/Home_Map.html";

  return (
    <div className="app-container">
      {/* Floating Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo" onClick={handleLogoClick} style={{ cursor: "pointer" }}>
                <img src="/logo3.png" alt="Logo" />
        </div>
          <h1 className="app-title">Park-A-Don</h1>
        </div>
        <div className="tab-bar">
          <div className={`tab ${activeTab === "map" ? "active" : ""}`} onClick={() => handleTabClick("map")}>Map</div>
          <div className={`tab ${openDropdown === "filters" ? "active" : ""}`} onClick={() => handleTabClick("filters")}>Filters</div>
          <div className={`tab ${openDropdown === "info" ? "active" : ""}`} onClick={() => handleTabClick("info")}>Info</div>
          <div className={`tab ${openDropdown === "risk" ? "active" : ""}`} onClick={() => handleTabClick("risk")}>Risk Check</div>
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
              {/* Map View */}
              <div className="filter-section">
                <div className="section-title">Map View</div>
                <div className="filter-buttons">
                  <button
                    className={filters.mapView === "standard" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "standard"); }}
                  >
                     Standard Map
                  </button>
                  <button
                    className={filters.mapView === "heatmap" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "heatmap"); }}
                  >
                     Heatmap View
                  </button>
                  <button
                    className={filters.mapView === "streetHours" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "streetHours"); }}
                  >
                     Street Parking Hours
                  </button>
                  <button
                    className={filters.mapView === "combinedView" ? "selected" : ""}
                    onClick={(e) => { e.stopPropagation(); handleFilterChange("mapView", "combinedView"); }}
                  >
                     Combined View
                  </button>
                </div>

                {/* Regenerate Button - Street Parking Hours */}
                {filters.mapView === "streetHours" && (
                  <div style={{ marginTop: '15px' }}>
                    <button
                      className="regenerate-button"
                      onClick={(e) => { 
                        e.stopPropagation(); 
                        regenerateMap(); 
                      }}
                      disabled={regenerating}
                      style={{
                        width: '100%',
                        padding: '12px',
                        backgroundColor: regenerating ? '#ccc' : '#00695c',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: 'bold',
                        cursor: regenerating ? 'not-allowed' : 'pointer',
                        transition: 'all 0.3s ease'
                      }}
                    >
                      {regenerating ? '🔄 Updating...' : '🔄 Update to Current Time'}
                    </button>
                    {lastUpdate && (
                      <div style={{
                        marginTop: '8px',
                        fontSize: '11px',
                        color: '#666',
                        textAlign: 'center'
                      }}>
                        Last updated: {lastUpdate}
                      </div>
                    )}
                  </div>
                )}

                {/* Regenerate Button - Combined View */}
                {filters.mapView === "combinedView" && (
                  <div style={{ marginTop: '15px' }}>
                    <button
                      className="regenerate-button"
                      onClick={(e) => { 
                        e.stopPropagation(); 
                        regenerateCombinedMap(); 
                      }}
                      disabled={regenerating}
                      style={{
                        width: '100%',
                        padding: '12px',
                        backgroundColor: regenerating ? '#ccc' : '#00695c',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: 'bold',
                        cursor: regenerating ? 'not-allowed' : 'pointer',
                        transition: 'all 0.3s ease'
                      }}
                    >
                      {regenerating ? '🔄 Updating...' : '🔄 Update to Current Time'}
                    </button>
                    {lastUpdateCombined && (
                      <div style={{
                        marginTop: '8px',
                        fontSize: '11px',
                        color: '#666',
                        textAlign: 'center'
                      }}>
                        Last updated: {lastUpdateCombined}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Availability */}
              <div className="filter-section">
                <div className="section-title">Availability</div>
                <div className="filter-buttons">
                  <button className={filters.availability === "all" ? "selected" : ""} onClick={() => handleFilterChange("availability", "all")}>All Spots</button>
                  <button className={filters.availability === "available" ? "selected" : ""} onClick={() => handleFilterChange("availability", "available")}>Available Only</button>
                  <button className={filters.availability === "occupied" ? "selected" : ""} onClick={() => handleFilterChange("availability", "occupied")}>Occupied</button>
                </div>
              </div>

              {/* Price Range */}
              <div className="filter-section">
                <div className="section-title">Price Range</div>
                <div className="filter-buttons">
                  <button className={filters.priceRange === "all" ? "selected" : ""} onClick={() => handleFilterChange("priceRange", "all")}>All Prices</button>
                  <button className={filters.priceRange === "free" ? "selected" : ""} onClick={() => handleFilterChange("priceRange", "free")}>Free</button>
                  <button className={filters.priceRange === "low" ? "selected" : ""} onClick={() => handleFilterChange("priceRange", "low")}>$ Low ($0-5)</button>
                  <button className={filters.priceRange === "medium" ? "selected" : ""} onClick={() => handleFilterChange("priceRange", "medium")}>$ Medium ($5-15)</button>
                  <button className={filters.priceRange === "high" ? "selected" : ""} onClick={() => handleFilterChange("priceRange", "high")}>$$ High ($15+)</button>
                </div>
              </div>

              {/* Distance */}
              <div className="filter-section">
                <div className="section-title">Distance</div>
                <div className="filter-buttons">
                  <button className={filters.distance === "all" ? "selected" : ""} onClick={() => handleFilterChange("distance", "all")}>Any Distance</button>
                  <button className={filters.distance === "near" ? "selected" : ""} onClick={() => handleFilterChange("distance", "near")}>Within 0.5 mi</button>
                  <button className={filters.distance === "medium" ? "selected" : ""} onClick={() => handleFilterChange("distance", "medium")}>Within 1 mi</button>
                  <button className={filters.distance === "far" ? "selected" : ""} onClick={() => handleFilterChange("distance", "far")}>Within 2 mi</button>
                </div>
              </div>

              {/* Parking Type */}
              
            </div>

            <div className="modal-actions">
              <button className="reset-button" onClick={resetFilters}>Reset All Filters</button>
              <button className="apply-button" onClick={closeModal}>Apply Filters</button>
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

 {/* Risk Check Modal */}
{openDropdown === "risk" && (
  <>
    <div className="modal-overlay" onClick={closeModal}></div>
    <div className="info-modal">
      <div className="modal-header">
        <h2>Risk Check</h2>
        <button className="close-modal" onClick={closeModal}>✕</button>
      </div>
      <div className="info-content">
        <label 
          htmlFor="risk-address" 
          style={{color: '#e8f5f3', fontWeight: 500, marginBottom: '0.5rem', display: 'block'}}
        >
          Enter Street Name:
        </label>
        <input 
          id="risk-address" 
          type="text" 
          placeholder="Example: MASON ST or howard street" 
          className="risk-input"
          onKeyPress={(e) => {
            if (e.key === 'Enter') handleRiskCheck();
          }}
        />
        <button 
          className="apply-button" 
          style={{marginTop:'1rem', width: 'auto', minWidth: '150px'}}
          onClick={handleRiskCheck}
          disabled={riskLoading}
        >
          {riskLoading ? "Checking..." : "Check Risk"}
        </button>
        
        {riskError && (
          <div style={{
            color:'#ff6b6b', 
            marginTop:'1rem', 
            padding: '0.5rem',
            backgroundColor: 'rgba(255,107,107,0.1)',
            borderRadius: '4px'
          }}>
            {riskError}
          </div>
        )}
        
        {riskResult && (
          <div style={{
            marginTop:'1rem', 
            color:'#e8f5f3',
            backgroundColor: 'rgba(255,255,255,0.05)',
            padding: '1rem',
            borderRadius: '8px',
            border: `2px solid ${riskResult.risk_color || '#00FF00'}`
          }}>
            <h3 style={{
              color: riskResult.risk_color || '#00FF00', 
              marginBottom: '0.75rem',
              fontSize: '1.3rem',
              fontWeight: 'bold'
            }}>
              {riskResult.recommendation || 'Risk analysis complete'}
            </h3>
            
            <div style={{
              marginBottom: '0.75rem', 
              padding: '0.5rem',
              backgroundColor: 'rgba(255,255,255,0.03)',
              borderRadius: '4px'
            }}>
              <div style={{marginBottom: '0.3rem'}}>
                <strong>Zone ID:</strong> {riskResult.zone_id}
              </div>
              <div style={{marginBottom: '0.3rem'}}>
                <strong>Risk Score:</strong> <span style={{
                  color: riskResult.risk_color,
                  fontWeight: 'bold',
                  fontSize: '1.1rem'
                }}>{riskResult.risk_score}</span> / 100
              </div>
              <div>
                <strong>Risk Level:</strong> <span style={{color: riskResult.risk_color}}>{riskResult.risk_level}</span>
              </div>
            </div>
            
            {riskResult.matched_address && (
              <div style={{
                marginBottom: '0.75rem',
                padding: '0.5rem',
                backgroundColor: 'rgba(255,255,255,0.03)',
                borderRadius: '4px'
              }}>
                <strong>📍 Matched Address:</strong>
                <div style={{marginTop: '0.25rem'}}>{riskResult.matched_address}</div>
              </div>
            )}
            
            {riskResult.peak_info && (
              <div style={{
                marginBottom: '0.75rem',
                padding: '0.5rem',
                backgroundColor: riskResult.is_peak_time 
                  ? 'rgba(255,0,0,0.1)' 
                  : 'rgba(0,255,0,0.05)',
                borderRadius: '4px',
                border: riskResult.is_peak_time 
                  ? '1px solid rgba(255,0,0,0.3)' 
                  : '1px solid rgba(0,255,0,0.2)'
              }}>
                <div style={{marginBottom: '0.25rem'}}>
                  <strong>⏰ Peak Time Status:</strong> {riskResult.is_peak_time ? "⚠️ YES - High Risk NOW!" : "✅ No - Safe Time"}
                </div>
                <div style={{fontSize: '0.9rem', opacity: 0.8}}>
                  Most tickets on <strong>{riskResult.peak_info.day}s</strong> around <strong>{riskResult.peak_info.hour}:00</strong>
                </div>
              </div>
            )}
            
            {riskResult.statistics && (
              <div style={{
                marginBottom: '0.75rem',
                padding: '0.5rem',
                backgroundColor: 'rgba(255,255,255,0.03)',
                borderRadius: '4px'
              }}>
                <div style={{marginBottom: '0.3rem'}}>
                  <strong>📊 Statistics:</strong>
                </div>
                <div style={{fontSize: '0.95rem', paddingLeft: '0.5rem'}}>
                  <div style={{marginBottom: '0.2rem'}}>
                    • Total Tickets: <strong>{riskResult.statistics.total_tickets}</strong>
                  </div>
                  <div style={{marginBottom: '0.2rem'}}>
                    • Per Day: <strong>{riskResult.statistics.tickets_per_day}</strong> tickets/day
                  </div>
                  <div>
                    • Data Period: <strong>{riskResult.statistics.data_period_days}</strong> days
                  </div>
                </div>
              </div>
            )}
            
            {riskResult.location && (
              <div style={{
                fontSize: '0.85rem', 
                opacity: 0.7, 
                marginTop: '0.5rem',
                padding: '0.5rem',
                backgroundColor: 'rgba(0,0,0,0.2)',
                borderRadius: '4px'
              }}>
                <strong>🗺️ Coordinates:</strong>
                <div style={{marginTop: '0.25rem'}}>
                  {riskResult.location.latitude.toFixed(6)}, {riskResult.location.longitude.toFixed(6)}
                </div>
              </div>
            )}

            {riskResult.timestamp && (
              <div style={{
                fontSize: '0.75rem', 
                opacity: 0.5, 
                marginTop: '0.5rem',
                textAlign: 'center'
              }}>
                Analysis time: {new Date(riskResult.timestamp).toLocaleString()}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  </>
)}

      {/* Loading Overlay */}
      {(loading || regenerating) && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <div className="loading-text">
            {regenerating ? 'Regenerating map with current time...' : 'Loading map...'}
          </div>
        </div>
      )}

      {/* Map Background */}
      <div className="map-container">
        <iframe 
          key={`${filters.mapView}-${mapKey}`}
          src={
            filters.mapView === "heatmap"
              ? "/maps/usf_parking_heatmap.html"
              : filters.mapView === "streetHours"
                ? `/maps/usf_parking_current_status.html?t=${mapKey}`
                : filters.mapView === "combinedView"
                  ? `/maps/usf_parking_combined.html?t=${mapKey}`
                  : defaultMap
          }
          title="Map"
        />
      </div>
    </div>
  );
};

export default App;