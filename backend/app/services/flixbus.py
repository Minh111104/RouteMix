import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_CITIES_URL = "https://global.api.flixbus.com/search/autocomplete/cities"
_SEARCH_URL = "https://global.api.flixbus.com/search/service/v4/search"
_TIMEOUT = 10.0
_HEADERS = {"x-locale": "en_US", "User-Agent": "Mozilla/5.0"}


def _city_from_address(address: str) -> str:
    return address.split(",")[0].strip()


async def _get_city_id(city: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                _CITIES_URL,
                params={"q": city, "lang": "en", "flixbus_cities_only": "false", "stations": "false"},
                headers=_HEADERS,
            )
            if r.status_code == 200:
                hits = r.json()
                if hits:
                    return hits[0]["id"]
    except Exception as exc:
        logger.debug("FlixBus city lookup error for %r: %s", city, exc)
    return None


async def search_buses(origin: str, destination: str, departure_date: str) -> Optional[dict]:
    """
    Search FlixBus for the cheapest available bus on departure_date (YYYY-MM-DD).
    Returns dict or None if no service / API unreachable.
    """
    origin_city = _city_from_address(origin)
    dest_city = _city_from_address(destination)

    from_id, to_id = await asyncio.gather(
        _get_city_id(origin_city), _get_city_id(dest_city)
    )
    if not from_id or not to_id:
        logger.info("FlixBus: no city ID for %r or %r", origin_city, dest_city)
        return None

    y, m, d = departure_date.split("-")
    fb_date = f"{d}.{m}.{y}"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                _SEARCH_URL,
                params={
                    "from_city_id": from_id,
                    "to_city_id": to_id,
                    "departure_date": fb_date,
                    "pax": 1,
                    "products[product]": "adult",
                    "currency": "USD",
                },
                headers=_HEADERS,
            )
    except Exception as exc:
        logger.warning("FlixBus search request failed: %s", exc)
        return None

    if r.status_code != 200:
        logger.info("FlixBus returned HTTP %d for %s→%s", r.status_code, origin_city, dest_city)
        return None

    trips = r.json().get("trips", [])
    available = [t for t in trips if t.get("status") == "available"]
    if not available:
        logger.info("FlixBus: no available trips for %s→%s on %s", origin_city, dest_city, departure_date)
        return None

    cheapest = min(
        available,
        key=lambda t: t.get("prices", {}).get("adult", {}).get("total", float("inf")),
    )
    price = cheapest.get("prices", {}).get("adult", {}).get("total")
    dur = cheapest.get("duration", {})
    duration_minutes = dur.get("hours", 0) * 60 + dur.get("minutes", 0)

    if not price or not duration_minutes:
        return None

    logger.info("FlixBus: found trip %s→%s $%.2f %dmin", origin_city, dest_city, price, duration_minutes)
    return {
        "cost_usd": float(price),
        "duration_minutes": duration_minutes,
        "departure_time": cheapest.get("departure", {}).get("date"),
        "arrival_time": cheapest.get("arrival", {}).get("date"),
        "carrier": "FlixBus",
        "source": "live",
    }
