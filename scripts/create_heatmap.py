"""Write a static copy of the "Heatmap" map into the React public folder.

The app normally gets this map live from the backend (GET /maps/heatmap), which
rebuilds it for the current hour. Use this script to export a snapshot for serving
the frontend without the backend.

    python scripts/create_heatmap.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parking_maps  # noqa: E402

if __name__ == "__main__":
    path, stats = parking_maps.save_static("heatmap")
    print(f"Citations this hour: {stats['citations_this_hour']} of {stats['citations_total']}")
    print(f"Hotspot markers: {stats['clusters_shown']} of {stats['clusters_total']}")
    print(f"Saved {path}")
