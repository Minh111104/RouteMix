import httpx
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


async def search_flights(
    origin_iata: str,     # e.g. "TOL"
    dest_iata: str,       # e.g. "SJC"
    departure_date: str,  # YYYY-MM-DD
    api_key: str,
    max_results: int = 3,
) -> List[dict]:
    """
    Search flights via Serpapi's Google Flights engine using IATA airport codes.

    Returns list of dicts with:
      duration_minutes, cost_usd, carrier, departure_time, arrival_time
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SERPAPI_URL,
            params={
                "engine": "google_flights",
                "departure_id": origin_iata,
                "arrival_id": dest_iata,
                "outbound_date": departure_date,
                "currency": "USD",
                "hl": "en",
                "adults": 1,
                "type": 2,  # one-way
                "api_key": api_key,
            },
            timeout=20.0,
        )

    if resp.status_code != 200:
        logger.warning("Serpapi request failed (%s): %s", resp.status_code, resp.text[:300])
        return []

    data = resp.json()
    if "error" in data:
        logger.warning("Serpapi error for %s→%s: %s", origin_iata, dest_iata, data["error"])
        return []

    all_offers = data.get("best_flights", []) + data.get("other_flights", [])
    results = []

    for offer in all_offers[:max_results]:
        try:
            legs = offer["flights"]
            first_leg = legs[0]
            last_leg = legs[-1]
            airline = first_leg.get("airline", "Unknown airline")
            flight_number = first_leg.get("flight_number", "")
            results.append({
                "duration_minutes": int(offer["total_duration"]),
                "cost_usd": float(offer["price"]),
                "carrier": f"{airline} {flight_number}".strip(),
                "departure_time": first_leg["departure_airport"]["time"],
                "arrival_time": last_leg["arrival_airport"]["time"],
            })
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Skipping malformed flight offer: %s", exc)

    return results
