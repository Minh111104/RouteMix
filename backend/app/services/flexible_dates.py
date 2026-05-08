import asyncio
import logging
from datetime import date, timedelta
from typing import List, Optional

from app.services.airports import find_nearest_airports
from app.services.flixbus import search_buses
from app.services.google_routes import geocode_address
from app.services.serpapi import search_flights

logger = logging.getLogger(__name__)


async def _empty() -> list:
    return []


async def _search_one_date(
    d: date,
    origin: str,
    destination: str,
    orig_iata: Optional[str],
    dest_iata: Optional[str],
    serpapi_key: str,
) -> dict:
    date_str = d.isoformat()

    flight_task = (
        search_flights(orig_iata, dest_iata, date_str, serpapi_key, max_results=1)
        if orig_iata and dest_iata and serpapi_key
        else _empty()
    )

    flights, bus = await asyncio.gather(flight_task, search_buses(origin, destination, date_str), return_exceptions=True)

    min_flight = None
    if isinstance(flights, list) and flights:
        min_flight = round(min(f["cost_usd"] for f in flights), 2)

    min_bus = None
    if isinstance(bus, dict) and bus:
        min_bus = round(bus["cost_usd"], 2)

    return {"date": date_str, "min_flight_usd": min_flight, "min_bus_usd": min_bus}


async def get_flexible_dates(
    origin: str,
    destination: str,
    center_date: str,
    google_key: str,
    serpapi_key: str,
    days: int = 3,
) -> dict:
    """
    Search ±days around center_date for flight and bus prices.
    Returns dict with keys: dates (list), origin_iata, dest_iata.
    """
    center = date.fromisoformat(center_date)
    date_range = [center + timedelta(days=d) for d in range(-days, days + 1)]

    origin_coords, dest_coords = await asyncio.gather(
        geocode_address(origin, google_key),
        geocode_address(destination, google_key),
    )

    orig_iata = dest_iata = None
    if origin_coords and dest_coords:
        orig_airports = find_nearest_airports(*origin_coords, max_results=3, commercial_only=True)
        dest_airports = find_nearest_airports(*dest_coords, max_results=3, commercial_only=True)
        if orig_airports and dest_airports:
            orig_iata = orig_airports[0]["iata"]
            dest_iata = dest_airports[0]["iata"]
            logger.info("Flexible dates: %s → %s", orig_iata, dest_iata)

    results = await asyncio.gather(
        *[
            _search_one_date(d, origin, destination, orig_iata, dest_iata, serpapi_key)
            for d in date_range
        ],
        return_exceptions=True,
    )

    dates = [r for r in results if isinstance(r, dict)]
    return {"dates": dates, "origin_iata": orig_iata, "dest_iata": dest_iata}
