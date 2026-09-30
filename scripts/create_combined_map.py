"""Write a static copy of the "Combined View" map into the React public folder.

The app normally gets this map live from the backend (GET /maps/combined), which
rebuilds it for the current hour. Use this script to export a snapshot for serving
the frontend without the backend.

    python scripts/create_combined_map.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parking_maps  # noqa: E402

if __name__ == "__main__":
    path, stats = parking_maps.save_static("combined")
    labels = dict(parking_maps.LEGEND_ROWS)
    print(f"Regulations: {stats['zones']} zones")
    for color, count in sorted(stats["colors"].items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}  {labels.get(color, color)}")
    if "citations" in stats:
        print(f"Heatmap: {stats['citations']} citations within "
              f"{parking_maps.HEATMAP_RADIUS_MILES} mi of campus")
        print(f"Clusters: showing top {stats['clusters_shown']} of {stats['clusters_total']}")
    print(f"Saved {path}")
