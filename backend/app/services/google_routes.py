import httpx
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Rough gas cost: 30 MPG at $3.50/gal
_GAS_COST_PER_METER = (1 / 1609.34) / 30 * 3.50  # USD/m


def _parse_duration_seconds(duration_str: str) -> int:
    """Parse Google Routes duration string like '18600s' to int seconds."""
    return int(duration_str.rstrip("s"))


async def geocode_address(address: str, api_key: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for an address, or None on failure."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GEOCODE_API_URL,
            params={"address": address, "key": api_key},
            timeout=10.0,
        )
    if resp.status_code != 200:
        logger.error("Geocode failed (%s): %s", resp.status_code, resp.text[:200])
        return None
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        logger.warning("Geocode returned no results for: %s", address)
        return None
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


async def get_driving_route(
    origin: str,
    destination: str,
    api_key: str,
) -> Optional[dict]:
    """
    Returns dict with keys: duration_minutes, distance_km, cost_usd
    or None if the request fails or returns no routes.
    """
    payload = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
        "computeAlternativeRoutes": False,
        "units": "METRIC",
    }
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(ROUTES_API_URL, json=payload, headers=headers, timeout=15.0)

    if resp.status_code != 200:
        logger.error("Driving route failed (%s): %s", resp.status_code, resp.text[:200])
        return None

    routes = resp.json().get("routes", [])
    if not routes:
        return None

    route = routes[0]
    duration_s = _parse_duration_seconds(route["duration"])
    distance_m = route["distanceMeters"]

    return {
        "duration_minutes": round(duration_s / 60),
        "distance_km": round(distance_m / 1000, 1),
        "cost_usd": round(distance_m * _GAS_COST_PER_METER, 2),
        "polyline": route.get("polyline", {}).get("encodedPolyline"),
    }


async def get_transit_route(
    origin: str,
    destination: str,
    departure_time: str,
    api_key: str,
) -> Optional[dict]:
    """
    Returns dict with keys: duration_minutes, cost_usd
    or None if no transit route found.

    cost_usd may be 0.0 if Google doesn't return fare data for this route.
    """
    # Ensure the timestamp ends with Z for UTC
    if not departure_time.endswith("Z"):
        departure_time = departure_time + "Z"

    payload = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "TRANSIT",
        "transitPreferences": {"routingPreference": "FEWER_TRANSFERS"},
        "departureTime": departure_time,
        "computeAlternativeRoutes": False,
        "units": "METRIC",
    }
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.legs.travelAdvisory.transitFare",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(ROUTES_API_URL, json=payload, headers=headers, timeout=15.0)

    if resp.status_code != 200:
        # 400 usually means no transit network connects these locations (expected for long routes)
        level = logger.debug if resp.status_code == 400 else logger.warning
        level("Transit route failed (%s): %s", resp.status_code, resp.text[:200])
        return None

    routes = resp.json().get("routes", [])
    if not routes:
        return None

    route = routes[0]
    duration_s = _parse_duration_seconds(route["duration"])

    cost_usd = 0.0
    for leg in route.get("legs", []):
        fare = leg.get("travelAdvisory", {}).get("transitFare")
        if fare:
            cost_usd += float(fare.get("units", 0)) + float(fare.get("nanos", 0)) / 1e9

    return {
        "duration_minutes": round(duration_s / 60),
        "cost_usd": round(cost_usd, 2),
    }
