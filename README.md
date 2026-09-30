# Park-A-Don


**Park-A-Don** is a React-based interactive map application for University of San Francisco (USFCA), designed to help users find parking spots efficiently. It includes multiple map views, filters, and a risk assessment tool for street parking.

---

## Screenshot

![Park-A-Don Screenshot](frontend/my-app/public/Screenshot.png)  
*Example of USFCA map with filters and street parking risk overlay.*

---

## Features

- **Map Views**
  - Standard Map: Default view of USFCA parking areas
  - Heatmap: Visualizes parking density
  - Street Parking Hours: Shows availability by time
  - Combined View: Merges multiple datasets

- **Filters**
  - Availability: All, available, or occupied
  - Price Range: Free, low, medium, high
  - Distance: Any or specific radius

- **Risk Assessment**
  - Input street names to check parking risk
  - Provides risk score, level, peak times, matched address, and coordinates

- **Interactive UI**
  - Floating top bar with tabs for filters, info, and risk check
  - Responsive modals
  - Click logo to return to default map
  - Smooth transitions

- **Map Updates**
  - Real-time regeneration of street parking hours or combined map
  - Loading overlay during updates

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Matthew-Vanhoomissen/Deploy-2025.git
cd Deploy-2025
```

2. Set up the Python backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Install the frontend dependencies (the React app lives in `frontend/my-app`):

```bash
cd frontend/my-app
npm install
```

4. Copy `.env.example` to `.env` and fill in any keys you have. Everything works
   without them; a `SODA_APP_TOKEN` just raises the DataSF rate limit.

---
## Usage

1. **Start the Flask backend** — from the repository root:

   ```bash
   .venv/bin/python parking.py
   ```

   The API starts at `http://localhost:5001/`. On boot it pulls the last 90 days
   of SFMTA citations near campus, caches them to `data/citations_cache.csv`, and
   clusters them into risk zones (this takes a few seconds). If DataSF is
   unreachable it falls back to the cache.

2. **Start the React frontend** — in a second terminal:

   ```bash
   cd frontend/my-app
   npm start
   ```

   The app opens at `http://localhost:3000/`. Alternatively, run
   `npm run build` and the Flask server will serve the built app from
   `http://localhost:5001/` on its own.

3. **Using the app**
   - Use the **tab bar** to switch between **Map**, **Filters**, **Info**, and **Risk Check**.
   - Under **Filters -> Map View**, pick **Standard**, **Heatmap**, **Street Parking Hours**, or **Combined View**.
   - Enter a street name in **Risk Check** to view risk information. A dropdown
     suggests matching streets as you type, with the citation count beside each
     one; use the arrow keys and Enter, or click a suggestion, to run the check.

---
## Risk-check autocomplete

`GET /streets` returns the distinct street names found in the citation data,
most-ticketed first. There are only a few hundred, so the frontend fetches the
list once when the Risk Check panel opens and filters it locally — no request per
keystroke. Streets starting with what you typed rank above ones merely containing
it, the typed portion is bolded, and the list is capped at 8.

Every suggestion is derived from the same address column `/zone-info` matches
against, so nothing the dropdown offers can be a dead end. That also makes the
dropdown the fix for spellings you could not guess: the feed contains
`JOHN F KENNNEDY DR` (with the typo) and `JFK DR`, and typing "ken" or "jfk"
surfaces whichever one actually exists.

Both sides normalize street names the same way (`normalize_addr` in `parking.py`,
`normalizeStreet` in `App.js`), expanding long suffixes to the abbreviations SFMTA
stores, so "hayes street" finds `HAYES ST` and "geary boulevard" finds
`GEARY BLVD`.

---
## API

| Endpoint | Description |
| --- | --- |
| `GET /maps/heatmap` | "Heatmap" map, rendered for the current hour |
| `GET /maps/street-hours` | "Street Parking Hours" map, rendered for the current hour |
| `GET /maps/combined` | "Combined View" map, rendered for the current hour |
| `GET /zones` | Parking regulations near campus as GeoJSON |
| `GET /zone-info/<street>` | Risk details for the zone matching a street name |
| `GET /streets` | Street names for the risk-check autocomplete (`?q=`, `?limit=`) |
| `GET /risk-score/<zone_id>` | Risk details for one cluster |
| `GET /safest-zones` | Five lowest-risk zones right now |
| `GET /danger-zones` | Five highest-risk zones right now |

---
## How the maps are served

`Standard Map` is a static Folium file in `frontend/my-app/public/maps/`.

The other three views depend on the current time, so the backend renders them on
request:

| View | Route | What the time changes |
| --- | --- | --- |
| Heatmap | `GET /maps/heatmap` | Ticket density for citations issued within an hour of now |
| Street Parking Hours | `GET /maps/street-hours` | Street colours by the limit in force now |
| Combined View | `GET /maps/combined` | Both of the above on one map |

The Heatmap answers "where do tickets get written *at this time of day*" rather
than averaging the whole 90-day window — it is a very different picture at 8am
(~9,800 citations in range) than at 3am (~60). The narrower this-hour-and-weekday
cut and the full 90 days are available as layer toggles, as is the aggregate
heatmap on the Combined View.

On the Heatmap and Combined views, the red markers are clickable: each one reports
how many citations fall in that cluster and what share of the shown citations that
is, the main reasons for the tickets with counts and percentages, the busiest hour
and weekday, the typical and total fine, and the most-cited addresses. SFMTA ships
violation descriptions as abbreviations (`STR CLEAN`, `RES/OT`); `VIOLATION_NAMES`
in `parking_maps.py` expands all 58 that appear in the feed, and any future code
falls through to the raw abbreviation rather than being dropped.

Rendered HTML is cached per hour — SFMTA regulation windows start and end on the
hour, and citations are bucketed by hour, so that is as often as anything can
change. The response carries a `Cache-Control` that expires at the top of the next
hour, and the frontend reloads these views when the hour turns, so a page left
open stays current.

Because these views come from the backend, **the backend must be running** for
them to load. `parking_maps.py` holds the builders; the maps and `GET /zones` read
the same regulation data through `parking_zones.py`, and the heatmap layers read
the same citation cache that powers the risk scoring, so the API and the maps
cannot disagree.

To export static snapshots instead (for serving the frontend with no backend):

```bash
.venv/bin/python scripts/create_heatmap.py
.venv/bin/python scripts/create_line_map.py
.venv/bin/python scripts/create_combined_map.py
```

These write into `frontend/my-app/public/maps/`. A snapshot is frozen at the hour
it was generated, which is why the app prefers the live routes.

---
## Styling

The app uses a clean and modern design:
- Font: `Lexend Deca`  
- Color scheme: dark mode with clear contrast  
- Responsive layout for all screen sizes  
- Map, tabs, and controls are visually distinct and user-friendly  

---

## Credits

This project was developed at **USFCA**.  

### Partners
- Matthew Vanhoomissen  
- Joshua Lim 
- Christopher Guillen Aguilar 

---
