// -------------------- Initialize Map --------------------
const map = L.map('map').setView([37.7765, -122.4505], 16);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// -------------------- Helper Functions --------------------
function getMaxHours(feature) {
    // First check if we have a max_hours property (from sample data)
    if (feature.properties.max_hours !== undefined) {
        return feature.properties.max_hours;
    }
    
    const begin = Number(feature.properties.hrs_begin || feature.properties.HRS_BEGIN);
    const end = Number(feature.properties.hrs_end || feature.properties.HRS_END);
    
    // Calculate allowed parking hours if times are valid
    if (!isNaN(begin) && !isNaN(end) && begin > 0 && end > 0) {
        const beginHours = Math.floor(begin / 100);
        const beginMinutes = begin % 100;
        const endHours = Math.floor(end / 100);
        const endMinutes = end % 100;
        const totalHours = (endHours + endMinutes / 60) - (beginHours + beginMinutes / 60);
        return totalHours > 0 ? totalHours : 0;
    }
    
    // Check REGULATION text for no parking
    const rule = ((feature.properties.regulation || feature.properties.REGULATION) || '').toUpperCase();
    if (rule.includes('NO PARKING') || rule.includes('TOW-AWAY') || rule.includes('NO STOPPING')) {
        return 0;
    }
    
    // Check for time limits in regulation text
    if (rule.includes('1 HR') || rule.includes('1HR') || rule.includes('1 HOUR')) {
        return 1;
    }
    if (rule.includes('2 HR') || rule.includes('2HR') || rule.includes('2 HOUR')) {
        return 2;
    }
    if (rule.includes('3 HR') || rule.includes('3HR') || rule.includes('3 HOUR')) {
        return 3;
    }
    if (rule.includes('4 HR') || rule.includes('4HR') || rule.includes('4 HOUR')) {
        return 4;
    }
    
    return null; // Unknown
}

function getColorByHours(hours) {
    if (hours === null) return "#808080";   // Unknown - Gray
    if (hours <= 0) return "#FF0000";       // No Parking - Red
    else if (hours === 1) return "#FFFF00"; // 1 hour - Yellow
    else if (hours === 2) return "#FFA500"; // 2 hours - Orange
    else return "#00FF00";                  // 3+ hours - Green
}

// -------------------- Add Legend FIRST --------------------
const legend = L.control({position: 'bottomright'});
legend.onAdd = function(map) {
    const div = L.DomUtil.create('div', 'info legend');
    div.innerHTML = `
        <strong>Parking Duration</strong><br>
        <i style="background:#FF0000"></i> No Parking<br>
        <i style="background:#FFFF00"></i> 1 Hour<br>
        <i style="background:#FFA500"></i> 2 Hours<br>
        <i style="background:#00FF00"></i> 3+ Hours<br>
        <i style="background:#808080"></i> Unknown
    `;
    return div;
};
legend.addTo(map);

// -------------------- Fetch & Display Zones --------------------
fetch("/zones")
    .then(res => res.json())
    .then(data => {
        console.log("Response data:", data);
        console.log("Total features:", data.features ? data.features.length : 0);
        
        if (!data.features || data.features.length === 0) {
            console.error("No features returned from server!");
            return;
        }
        
        console.log("Sample feature:", data.features[0]);
        console.log("Sample properties:", data.features[0].properties);
        console.log("Sample geometry type:", data.features[0].geometry.type);
        
        // Filter out features without geometry
        const validFeatures = data.features.filter(f => f.geometry !== null);
        console.log("Valid features with geometry:", validFeatures.length);
        
        if (validFeatures.length === 0) {
            console.error("No features have geometry!");
            return;
        }
        
        // Log some sample hours calculations
        console.log("Sample hours calculation:", getMaxHours(data.features[0]));
        console.log("Sample color:", getColorByHours(getMaxHours(data.features[0])));
        
        // -------------------- ADD GEOJSON LAYER --------------------
        const zonesLayer = L.geoJSON(data, {
            style: function(feature) {
                const hours = getMaxHours(feature);
                const color = getColorByHours(hours);
                console.log("Styling feature with hours:", hours, "color:", color);
                return {
                    color: color,
                    weight: 6,           // Thicker lines
                    opacity: 1,          // Full opacity
                    lineCap: 'butt',     // Square ends for better visibility
                    lineJoin: 'miter'    // Sharp corners
                };
            },
            onEachFeature: function(feature, layer) {
                const props = feature.properties;
                const hours = getMaxHours(feature);
                
                let popupContent = `<strong>Regulation:</strong> ${props.REGULATION || 'N/A'}<br>`;
                popupContent += `<strong>Days:</strong> ${props.DAYS || 'N/A'}<br>`;
                popupContent += `<strong>Hours:</strong> ${props.HRS_BEGIN || 'N/A'} - ${props.HRS_END || 'N/A'}<br>`;
                popupContent += `<strong>Max Parking:</strong> ${hours !== null ? hours + ' hours' : 'Unknown'}<br>`;
                if (props.EXCEPTIONS) popupContent += `<strong>Exceptions:</strong> ${props.EXCEPTIONS}<br>`;
                if (props.RPPAREA1) popupContent += `<strong>RPP Area:</strong> ${props.RPPAREA1}<br>`;
                
                layer.bindPopup(popupContent);
            }
        }).addTo(map);
        
        console.log("Zones layer added to map");
        
        // -------------------- Fetch Ticket Data & Heatmap --------------------
        fetch("/tickets")
            .then(res => res.json())
            .then(points => {
                console.log("Ticket points loaded:", points.length);
                if (points.length > 0) {
                    L.heatLayer(points, {
                        radius: 25,
                        blur: 15,
                        maxZoom: 17,
                        gradient: {0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 0.8: 'red'}
                    }).addTo(map);
                }
            })
            .catch(err => console.error("Error loading tickets:", err));
    })
    .catch(err => console.error("Error loading zones:", err));