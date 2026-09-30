"""Parking-regulation zones for USF, read from the SFMTA regulations export.

Both the Flask `/zones` endpoint and scripts/create_line_map.py read zones through
here so the API and the generated maps can never drift apart.
"""

import os

import pandas as pd
from shapely import wkt
from shapely.geometry import mapping

REGULATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "parking_regulations.csv")

# Bounding box around the USF campus; the export covers all of San Francisco.
USF_BOUNDS = {"lat_min": 37.774, "lat_max": 37.785, "lon_min": -122.460, "lon_max": -122.440}

DAY_NAMES = ["M", "TU", "W", "TH", "F", "SA", "SU"]


def _hhmm(value):
    """SFMTA stores times as an HHMM integer; return it as a string, or '' if absent."""
    if pd.isna(value) or value == "":
        return ""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return ""


def _optional_int(value):
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _text(value):
    return "" if pd.isna(value) else str(value)


def load_zones(bounds=USF_BOUNDS):
    """Return the regulations as a GeoJSON FeatureCollection, clipped to `bounds`.

    Pass bounds=None for the whole city.
    """
    df = pd.read_csv(REGULATIONS_PATH, low_memory=False)

    features = []
    for row in df.itertuples(index=False):
        shape = getattr(row, "shape", None)
        if not isinstance(shape, str):
            continue
        try:
            geom = wkt.loads(shape)
        except Exception:
            # A handful of rows in the export have malformed WKT.
            continue

        if bounds is not None:
            centroid = geom.centroid
            if not (bounds["lat_min"] <= centroid.y <= bounds["lat_max"]
                    and bounds["lon_min"] <= centroid.x <= bounds["lon_max"]):
                continue

        features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "objectid": _text(row.objectid),
                "regulation": _text(row.REGULATION),
                "days": _text(row.DAYS),
                "hours": _text(row.HOURS),
                "hrs_begin": _hhmm(row.HRS_BEGIN),
                "hrs_end": _hhmm(row.HRS_END),
                "max_hours": _optional_int(row.HRLIMIT),
                "exceptions": _text(row.EXCEPTIONS),
                "from_time": _text(row.FROM_TIME),
                "to_time": _text(row.TO_TIME),
                "rpparea1": _text(row.RPPAREA1),
                "agency": _text(row.AGENCY),
                "supervisor_district": _text(row.supervisor_district),
            },
        })

    return {"type": "FeatureCollection", "features": features}
