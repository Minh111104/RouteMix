import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


async def search_flights(
    origin: str,       # city name (e.g. "Bowling Green, OH") or IATA code
    destination: str,  # city name or IATA code
    departure_date: str,  # YYYY-MM-DD
    api_key: str,
    max_results: int = 3,
) -> List[dict]:
    """
    Search flights via Serpapi's Google Flights engine.

    Serpapi resolves city names to airports automatically, so no IATA
    lookup step is needed. The response includes the actual departure/arrival
    airport names and codes used, which we pass back to Google Routes to
    build the drive-to-airport and transit-from-airport legs.

    Returns list of dicts with:
      duration_minutes, cost_usd, carrier,
      departure_time, arrival_time,
      origin_airport_name, dest_airport_name,
      origin_iata, dest_iata
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SERPAPI_URL,
            params={
                "engine": "google_flights",
                "departure_id": origin,
                "arrival_id": destination,
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
        logger.warning("Serpapi error: %s", data["error"])
        return []

    # Serpapi splits results into best_flights and other_flights
    all_offers = data.get("best_flights", []) + data.get("other_flights", [])

    results = []
    for offer in all_offers[:max_results]:
        try:
            flight_legs = offer["flights"]
            first_leg = flight_legs[0]
            last_leg = flight_legs[-1]

            airline = first_leg.get("airline", "Unknown airline")
            flight_number = first_leg.get("flight_number", "")

            results.append({
                "duration_minutes": int(offer["total_duration"]),
                "cost_usd": float(offer["price"]),
                "carrier": f"{airline} {flight_number}".strip(),
                "departure_time": first_leg["departure_airport"]["time"],
                "arrival_time": last_leg["arrival_airport"]["time"],
                "origin_airport_name": first_leg["departure_airport"]["name"],
                "dest_airport_name": last_leg["arrival_airport"]["name"],
                "origin_iata": first_leg["departure_airport"]["id"],
                "dest_iata": last_leg["arrival_airport"]["id"],
            })
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Skipping malformed flight offer: %s", exc)

    return results
