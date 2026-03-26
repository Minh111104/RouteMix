import httpx
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_AIRPORTS_URL = "https://test.api.amadeus.com/v1/reference-data/locations/airports"
AMADEUS_FLIGHTS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def _parse_iso_duration(duration: str) -> int:
    """Parse ISO 8601 duration like 'PT2H30M' to minutes."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return hours * 60 + minutes


async def get_access_token(api_key: str, api_secret: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            AMADEUS_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": api_secret,
            },
            timeout=10.0,
        )
    if resp.status_code != 200:
        logger.error("Amadeus auth failed (%s): %s", resp.status_code, resp.text[:200])
        return None
    return resp.json().get("access_token")


async def find_airports_near(
    lat: float,
    lon: float,
    token: str,
    radius: int = 200,
    limit: int = 3,
) -> List[dict]:
    """Return list of airport dicts with iataCode, name, address, geoCode fields."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            AMADEUS_AIRPORTS_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "radius": radius,
                "page[limit]": limit,
                "sort": "relevance",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    if resp.status_code != 200:
        logger.warning("Airport search failed (%s): %s", resp.status_code, resp.text[:200])
        return []
    return resp.json().get("data", [])


async def search_flights(
    origin_iata: str,
    dest_iata: str,
    departure_date: str,  # YYYY-MM-DD
    token: str,
    max_results: int = 3,
) -> List[dict]:
    """
    Return list of flight dicts with:
    duration_minutes, cost_usd, carrier, departure_time, arrival_time,
    origin_iata, dest_iata
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            AMADEUS_FLIGHTS_URL,
            params={
                "originLocationCode": origin_iata,
                "destinationLocationCode": dest_iata,
                "departureDate": departure_date,
                "adults": 1,
                "max": max_results,
                "currencyCode": "USD",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
    if resp.status_code != 200:
        logger.warning("Flight search failed (%s): %s", resp.status_code, resp.text[:200])
        return []

    results = []
    for offer in resp.json().get("data", []):
        try:
            itinerary = offer["itineraries"][0]
            segment = itinerary["segments"][0]
            results.append({
                "duration_minutes": _parse_iso_duration(itinerary["duration"]),
                "cost_usd": float(offer["price"]["total"]),
                "carrier": f"{segment['carrierCode']}{segment['number']}",
                "departure_time": segment["departure"]["at"],
                "arrival_time": segment["arrival"]["at"],
                "origin_iata": origin_iata,
                "dest_iata": dest_iata,
            })
        except (KeyError, IndexError) as exc:
            logger.warning("Error parsing flight offer: %s", exc)

    return results
