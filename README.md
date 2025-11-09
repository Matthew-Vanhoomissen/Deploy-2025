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
git clone https://github.com/yourusername/park-a-don.git
cd park-a-don
```

2.	Install dependencies:
```bash 
npm install
```
3.	Start the frontend:

```bash
npm start
```
---
## Usage

1. **Start the Flask backend**  
   Open a terminal in the backend folder and run:  
   `python app.py`  
   The API will start at `http://localhost:5000/`.

2. **Start the React frontend**  
   Open a terminal in the frontend folder and run:  
   `npm install` (if dependencies aren’t installed yet)  
   `npm start`  
   The app will open in your default browser at `http://localhost:3000/`.

3. **Using the app**  
   - Click the **logo** to center the map on USFCA.  
   - Use the **tab bar** to switch between **Map**, **Filters**, **Info**, and **Risk Check**.  
   - Adjust filters to customize map views (**Standard**, **Heatmap**, **Street Hours**, **Combined View**).  
   - Click **Update to Current Time** on **Street Hours** or **Combined View** to regenerate the map.  
   - Enter a street name in **Risk Check** to view risk information.
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
