import React, { useState, useEffect } from "react";
import "./App.css";

const DEFAULT_FILTERS = {
  availability: "all",
  priceRange: "all",
  distance: "all",
  parkingType: "all",
  mapView: "standard"
};

const FILTER_SECTIONS = [
  { key: "mapView", title: "Map View", options: [
    ["standard", "🗺️ Standard Map"],
    ["heatmap", "🔥 Heatmap View"],
    ["streetHours", "🛣️ Street Parking Hours"],
    ["combinedView", "🔗 Combined View"]
  ]},
  { key: "availability", title: "Availability", options: [
    ["all", "All Spots"], ["available", "Available Only"], ["occupied", "Occupied"]
  ]},
  { key: "priceRange", title: "Price Range", options: [
    ["all", "All Prices"], ["free", "Free"], ["low", "$ Low ($0-5)"], ["medium", "$ Medium ($5-15)"], ["high", "$$ High ($15+)"]
  ]},
  { key: "distance", title: "Distance", options: [
    ["all", "Any Distance"], ["near", "Within 0.5 mi"], ["medium", "Within 1 mi"], ["far", "Within 2 mi"]
  ]},
  { key: "parkingType", title: "Parking Type", options: [
    ["all", "All Types"], ["garage", "🏢 Garage"], ["lot", "🅿️ Parking Lot"], ["street", "🛣️ Street Parking"]
  ]}
];

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:5001";

// These views depend on the current time -- street colours on the limit in force
// now, the heatmap on when tickets actually get written -- so the backend renders
// them per hour instead of serving a pre-rendered file.
const MAP_SOURCES = {
  standard: "/maps/Home_Map.html",
  heatmap: `${API_BASE}/maps/heatmap`,
  streetHours: `${API_BASE}/maps/street-hours`,
  combinedView: `${API_BASE}/maps/combined`
};

const LIVE_MAP_VIEWS = ["heatmap", "streetHours", "combinedView"];

const currentHour = () => {
  const now = new Date();
  return `${now.toDateString()}-${now.getHours()}`;
};

const TABS = [["map", "Map"], ["filters", "Filters"], ["info", "Info"], ["risk", "Risk Check"]];

const MAX_SUGGESTIONS = 8;

// Mirrors normalize_addr() on the backend so "hayes street" matches "HAYES ST"
// and "geary boulevard" matches "GEARY BLVD".
const STREET_SUFFIXES = {
  street: "st", avenue: "ave", boulevard: "blvd", road: "rd",
  drive: "dr", terrace: "ter", place: "pl", court: "ct",
  lane: "ln", parkway: "pkwy", highway: "hwy", circle: "cir",
  square: "sq", alley: "aly",
};

const SUFFIX_RE = new RegExp(`\\b(${Object.keys(STREET_SUFFIXES).join("|")})\\b`, "g");

const normalizeStreet = (value) =>
  value
    .toLowerCase()
    .replace(/\./g, "")
    .replace(SUFFIX_RE, (match) => STREET_SUFFIXES[match])
    .replace(/[^a-z0-9 ]/g, "")
    .trim();

// Streets starting with what was typed rank above ones merely containing it, and
// within each group the most-ticketed street comes first (the list arrives sorted).
const rankStreets = (streets, query) => {
  const needle = normalizeStreet(query);
  if (!needle) return [];
  const startsWith = [];
  const contains = [];
  for (const street of streets) {
    const index = normalizeStreet(street.name).indexOf(needle);
    if (index === 0) startsWith.push(street);
    else if (index > 0) contains.push(street);
    if (startsWith.length >= MAX_SUGGESTIONS) break;
  }
  return [...startsWith, ...contains].slice(0, MAX_SUGGESTIONS);
};

// Bold the part of the name the user has typed.
const HighlightedName = ({ name, query }) => {
  const at = normalizeStreet(name).indexOf(normalizeStreet(query));
  if (at < 0) return name;
  const end = at + normalizeStreet(query).length;
  return (
    <>
      {name.slice(0, at)}
      <strong>{name.slice(at, end)}</strong>
      {name.slice(end)}
    </>
  );
};

const Modal = ({ title, className, onClose, children }) => (
  <>
    <div className="modal-overlay" onClick={onClose}></div>
    <div className={className}>
      <div className="modal-header">
        <h2>{title}</h2>
        <button className="close-modal" onClick={onClose}>✕</button>
      </div>
      {children}
    </div>
  </>
);

const RiskResult = ({ result: r }) => {
  const color = r.risk_color || "#00FF00";
  return (
    <div className="risk-result" style={{ borderColor: color }}>
      <h3 style={{ color }}>{r.recommendation || "Risk analysis complete"}</h3>

      <div className="risk-block">
        <div><strong>Zone ID:</strong> {r.zone_id}</div>
        <div><strong>Risk Score:</strong> <span className="risk-score" style={{ color: r.risk_color }}>{r.risk_score}</span> / 100</div>
        <div><strong>Risk Level:</strong> <span style={{ color: r.risk_color }}>{r.risk_level}</span></div>
      </div>

      {r.matched_address && (
        <div className="risk-block">
          <strong>📍 Matched Address:</strong>
          <div>{r.matched_address}</div>
        </div>
      )}

      {r.peak_info && (
        <div className={`risk-block ${r.is_peak_time ? "peak" : "off-peak"}`}>
          <div><strong>⏰ Peak Time Status:</strong> {r.is_peak_time ? "⚠️ YES - High Risk NOW!" : "✅ No - Safe Time"}</div>
          <div className="risk-muted">
            Most tickets on <strong>{r.peak_info.day}s</strong> around <strong>{r.peak_info.hour}:00</strong>
          </div>
        </div>
      )}

      {r.statistics && (
        <div className="risk-block">
          <div><strong>📊 Statistics:</strong></div>
          <div className="risk-stats">
            <div>• Total Tickets: <strong>{r.statistics.total_tickets}</strong></div>
            <div>• Per Day: <strong>{r.statistics.tickets_per_day}</strong> tickets/day</div>
            <div>• Data Period: <strong>{r.statistics.data_period_days}</strong> days</div>
          </div>
        </div>
      )}

      {r.location && (
        <div className="risk-block risk-coords">
          <strong>🗺️ Coordinates:</strong>
          <div>{r.location.latitude.toFixed(6)}, {r.location.longitude.toFixed(6)}</div>
        </div>
      )}

      {r.timestamp && (
        <div className="risk-timestamp">Analysis time: {new Date(r.timestamp).toLocaleString()}</div>
      )}
    </div>
  );
};

// Whether a click landed outside every open panel, and so should close it.
// Exported for tests: the detached-target case below cannot be reproduced through
// React Testing Library, which defers unmounting until after the event bubbles.
export const isOutsideClick = (target) =>
  // React 18 flushes state synchronously during discrete events, so picking an
  // autocomplete suggestion unmounts it before this runs. closest() on a detached
  // node matches nothing, which used to read as an outside click and close the
  // panel; a target no longer in the document was inside something we re-rendered.
  target.isConnected &&
  !target.closest(".tab") &&
  !target.closest(".filter-modal") &&
  !target.closest(".info-modal");

const App = () => {
  const [openDropdown, setOpenDropdown] = useState(null);
  const [activeTab, setActiveTab] = useState("map");
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(false);
  const [hour, setHour] = useState(currentHour);

  // Risk Check states
  const [address, setAddress] = useState("");
  const [riskResult, setRiskResult] = useState(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState(null);

  // Autocomplete states
  const [streets, setStreets] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [highlighted, setHighlighted] = useState(-1);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    const iframe = document.querySelector(".map-container iframe");
    if (iframe) iframe.onload = () => setLoading(false);
  }, [filters.mapView, hour]);

  // The street list is a few hundred names, so fetch it once and filter locally.
  useEffect(() => {
    if (openDropdown !== "risk" || streets.length) return;
    let cancelled = false;
    fetch(`${API_BASE}/streets`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .then((data) => !cancelled && setStreets(data.streets || []))
      .catch(() => {}); // autocomplete is a convenience; typing still works without it
    return () => { cancelled = true; };
  }, [openDropdown, streets.length]);

  // Reload the live maps when the hour turns, so a page left open stays current.
  useEffect(() => {
    const tick = setInterval(() => setHour(currentHour()), 60000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (isOutsideClick(e.target)) setOpenDropdown(null);
    };
    window.addEventListener("click", handleClickOutside);
    return () => window.removeEventListener("click", handleClickOutside);
  }, []);

  const handleTabClick = (tab) => {
    setActiveTab(tab);
    setOpenDropdown(tab === "map" || openDropdown === tab ? null : tab);
  };

  const closeModal = () => {
    setOpenDropdown(null);
    setActiveTab("map");
    setRiskResult(null);
    setRiskError(null);
    setSuggestions([]);
    setShowSuggestions(false);
    setHighlighted(-1);
  };

  const handleFilterChange = (filterType, value) => {
    if (filterType === "mapView") setLoading(true);
    setFilters(prev => ({ ...prev, [filterType]: value }));
  };

  const handleRiskCheck = async (override) => {
    const query = (override ?? address).trim();
    if (!query) {
      setRiskError("Please enter a street name");
      return;
    }

    setRiskLoading(true);
    setRiskError(null);
    setRiskResult(null);

    try {
      const response = await fetch(`${API_BASE}/zone-info/${encodeURIComponent(query)}`);
      const data = await response.json();
      if (response.ok) setRiskResult(data);
      else setRiskError(data.error || "Error fetching risk data");
    } catch (err) {
      setRiskError("Server error: " + err.message);
    } finally {
      setRiskLoading(false);
    }
  };


  const handleAddressChange = (value) => {
    setAddress(value);
    const matches = rankStreets(streets, value);
    setSuggestions(matches);
    setShowSuggestions(matches.length > 0);
    setHighlighted(-1);
  };

  const closeSuggestions = () => {
    setShowSuggestions(false);
    setHighlighted(-1);
  };

  const pickSuggestion = (street) => {
    setAddress(street.name);
    setSuggestions([]);
    closeSuggestions();
    handleRiskCheck(street.name);
  };

  const handleAddressKeyDown = (e) => {
    const isOpen = showSuggestions && suggestions.length > 0;

    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        const matches = rankStreets(streets, address);
        if (matches.length) {
          setSuggestions(matches);
          setShowSuggestions(true);
        }
        return;
      }
      const last = suggestions.length - 1;
      setHighlighted((prev) =>
        e.key === "ArrowDown"
          ? (prev >= last ? 0 : prev + 1)
          : (prev <= 0 ? last : prev - 1)
      );
      return;
    }

    if (e.key === "Enter") {
      if (isOpen && highlighted >= 0) pickSuggestion(suggestions[highlighted]);
      else {
        closeSuggestions();
        handleRiskCheck();
      }
      return;
    }

    if (e.key === "Escape" || e.key === "Tab") closeSuggestions();
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
          {TABS.map(([tab, label]) => (
            <div
              key={tab}
              className={`tab ${(tab === "map" ? activeTab === "map" : openDropdown === tab) ? "active" : ""}`}
              onClick={() => handleTabClick(tab)}
            >
              {label}
            </div>
          ))}
        </div>
      </header>

      {openDropdown === "filters" && (
        <Modal title="Filter Parking Spots" className="filter-modal" onClose={closeModal}>
          <div className="filter-grid">
            {FILTER_SECTIONS.map(({ key, title, options }) => (
              <div className="filter-section" key={key}>
                <div className="section-title">{title}</div>
                <div className="filter-buttons">
                  {options.map(([value, label]) => (
                    <button
                      key={value}
                      className={filters[key] === value ? "selected" : ""}
                      onClick={(e) => { e.stopPropagation(); handleFilterChange(key, value); }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="modal-actions">
            <button className="reset-button" onClick={() => setFilters(DEFAULT_FILTERS)}>Reset All Filters</button>
            <button className="apply-button" onClick={closeModal}>Apply Filters</button>
          </div>
        </Modal>
      )}

      {openDropdown === "info" && (
        <Modal title="Information" className="info-modal" onClose={closeModal}>
          <div className="info-content">
            <button className="info-item">About</button>
            <button className="info-item">Help</button>
            <button className="info-item">Contact</button>
          </div>
        </Modal>
      )}

      {openDropdown === "risk" && (
        <Modal title="Risk Check" className="info-modal" onClose={closeModal}>
          <div className="info-content">
            <label htmlFor="risk-address" className="risk-label">Enter Street Name:</label>
            <div className="risk-autocomplete">
              <input
                id="risk-address"
                type="text"
                placeholder="Example: FULTON ST or hayes street"
                className="risk-input"
                value={address}
                onChange={(e) => handleAddressChange(e.target.value)}
                onKeyDown={handleAddressKeyDown}
                onFocus={() => suggestions.length && setShowSuggestions(true)}
                onBlur={() => setTimeout(closeSuggestions, 120)}
                autoComplete="off"
                role="combobox"
                aria-expanded={showSuggestions && suggestions.length > 0}
                aria-controls="risk-suggestions"
                aria-activedescendant={highlighted >= 0 ? `risk-suggestion-${highlighted}` : undefined}
              />
              {showSuggestions && suggestions.length > 0 && (
                <ul className="risk-suggestions" id="risk-suggestions" role="listbox">
                  {suggestions.map((street, i) => (
                    <li
                      key={street.name}
                      id={`risk-suggestion-${i}`}
                      role="option"
                      aria-selected={i === highlighted}
                      className={i === highlighted ? "highlighted" : ""}
                      onMouseEnter={() => setHighlighted(i)}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={(e) => { e.stopPropagation(); pickSuggestion(street); }}
                    >
                      <span className="suggestion-name">
                        <HighlightedName name={street.name} query={address} />
                      </span>
                      <span className="suggestion-count">{street.citations}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button className="apply-button risk-button" onClick={() => handleRiskCheck()} disabled={riskLoading}>
              {riskLoading ? "Checking..." : "Check Risk"}
            </button>
            {riskError && <div className="risk-error">{riskError}</div>}
            {riskResult && <RiskResult result={riskResult} />}
          </div>
        </Modal>
      )}

      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <div className="loading-text">Loading map...</div>
        </div>
      )}

      <div className="map-container">
        <iframe
          src={MAP_SOURCES[filters.mapView] || MAP_SOURCES.standard}
          title="Map"
          key={LIVE_MAP_VIEWS.includes(filters.mapView) ? `${filters.mapView}-${hour}` : filters.mapView}
        />
      </div>
    </div>
  );
};

export default App;
