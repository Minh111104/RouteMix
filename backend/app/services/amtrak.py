import math
from typing import Optional, Tuple


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _in_northeast(lat: float, lon: float) -> bool:
    """Covers Boston–DC Northeast Corridor (DC at -77.0 is the western anchor)."""
    return 38.5 < lat < 47.5 and -77.5 < lon < -69.5


def _in_pacific(lat: float, lon: float) -> bool:
    """Pacific coast corridor (CA, OR, WA)."""
    return 32.0 < lat < 49.5 and -124.5 < lon < -116.5


def _in_midwest(lat: float, lon: float) -> bool:
    """Great Lakes / Midwest hub region (Chicago-centric)."""
    return 36.0 < lat < 48.0 and -93.0 < lon < -80.0


def estimate_train(
    origin_coords: Tuple[float, float],
    dest_coords: Tuple[float, float],
) -> Optional[dict]:
    """
    Estimate an Amtrak trip using haversine distance and corridor-aware
    speed/pricing. Returns None for routes under 100 km (too short for
    intercity train).
    """
    lat1, lon1 = origin_coords
    lat2, lon2 = dest_coords
    straight_km = _haversine_km(lat1, lon1, lat2, lon2)

    if straight_km < 100:
        return None

    nec = _in_northeast(lat1, lon1) and _in_northeast(lat2, lon2)
    pac = _in_pacific(lat1, lon1) and _in_pacific(lat2, lon2)
    midwest = _in_midwest(lat1, lon1) and _in_midwest(lat2, lon2)

    if nec and straight_km < 750:
        speed_kmh = 95   # NE Regional avg incl. stops (DC segment runs faster than BOS segment)
        cost_per_km = 0.19
        corridor = "Northeast Regional"
    elif pac and straight_km < 1200:
        speed_kmh = 72   # Coast Starlight / Surfliner avg incl. stops
        cost_per_km = 0.14
        corridor = "Pacific Surfliner / Coast Starlight"
    elif midwest and straight_km < 600:
        speed_kmh = 78   # Wolverine / Blue Water avg
        cost_per_km = 0.13
        corridor = "Midwest Regional"
    elif straight_km <= 800:
        speed_kmh = 75
        cost_per_km = 0.13
        corridor = "Amtrak regional"
    elif straight_km <= 2500:
        speed_kmh = 65   # Long-distance trains avg incl. stops and delays
        cost_per_km = 0.09
        corridor = "Long-distance"
    else:
        speed_kmh = 60
        cost_per_km = 0.07
        corridor = "Long-distance"

    # Trains run ~15% longer paths than straight-line
    train_km = straight_km * 1.15
    duration_minutes = round(train_km / speed_kmh * 60)
    cost_usd = round(train_km * cost_per_km, 2)

    return {
        "cost_usd": cost_usd,
        "duration_minutes": duration_minutes,
        "distance_km": round(train_km, 1),
        "corridor": corridor,
        "source": "estimate",
    }
