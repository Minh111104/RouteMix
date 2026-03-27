import math
from functools import lru_cache
from typing import List

import airportsdata

# Name patterns that indicate a general-aviation or non-commercial airport.
# These appear in airport names like "Tiffin-Fostoria Regional Airport",
# "Defiance Memorial Airport", "Lenawee County Airport", "Moffett Federal Airfield".
_GA_NAME_PATTERNS = (
    "regional airport",
    "county airport",
    "municipal airport",
    "memorial airport",
    "federal airfield",
    "airfield",
    "airpark",
    "heliport",
    "seaplane",
    "private",
)


@lru_cache(maxsize=1)
def _load() -> dict:
    """Load IATA airport database once and cache in memory."""
    return airportsdata.load("IATA")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _is_commercial(ap: dict) -> bool:
    """
    Heuristic: skip airports whose name matches general-aviation patterns.

    Positive override: names containing "international", "metro", or "metropolitan"
    are always kept — this prevents incorrectly filtering airports like DTW
    ("Detroit Metro Wayne County Airport") which contains "county airport" as a
    substring but is clearly a major commercial hub.
    """
    name = ap.get("name", "").lower()
    if any(kw in name for kw in ("international", " metro ", "metropolitan")):
        return True
    return not any(pattern in name for pattern in _GA_NAME_PATTERNS)


def find_nearest_airports(
    lat: float,
    lon: float,
    max_results: int = 3,
    max_km: float = 500.0,
    commercial_only: bool = True,
) -> List[dict]:
    """
    Return up to max_results airports within max_km, sorted by distance.
    Each dict has: iata, name, city, lat, lon, distance_km.

    When commercial_only=True (default), GA airports identified by name pattern
    are excluded — this avoids wasting Serpapi calls on airports with no
    scheduled service.
    """
    nearby = []
    for iata, ap in _load().items():
        ap_lat = ap.get("lat")
        ap_lon = ap.get("lon")
        if not ap_lat or not ap_lon:
            continue
        if commercial_only and not _is_commercial(ap):
            continue
        dist = _haversine_km(lat, lon, float(ap_lat), float(ap_lon))
        if dist <= max_km:
            nearby.append({
                "iata": iata,
                "name": ap.get("name", ""),
                "city": ap.get("city", ""),
                "lat": float(ap_lat),
                "lon": float(ap_lon),
                "distance_km": round(dist, 1),
            })

    nearby.sort(key=lambda x: x["distance_km"])
    return nearby[:max_results]
