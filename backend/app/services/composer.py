import asyncio
import logging
from typing import List, Optional

from app.models.route import ComposedRoute, RouteSegment, SearchRequest, TransportMode
from app.services.google_routes import get_driving_route, get_transit_route
from app.services.serpapi import search_flights

logger = logging.getLogger(__name__)

# Rideshare fallback estimate
_RIDESHARE_COST_PER_KM = 1.50
_RIDESHARE_SPEED_KMH = 40

# Flat airport overhead: check-in + security + boarding
_AIRPORT_OVERHEAD_MINUTES = 90


async def _build_drive_only(
    origin: str,
    destination: str,
    google_key: str,
) -> Optional[ComposedRoute]:
    data = await get_driving_route(origin, destination, google_key)
    if not data:
        return None
    return ComposedRoute(
        route_type="drive_only",
        label="Drive only",
        segments=[
            RouteSegment(
                mode=TransportMode.DRIVE,
                from_location=origin,
                to_location=destination,
                duration_minutes=data["duration_minutes"],
                distance_km=data["distance_km"],
                cost_usd=data["cost_usd"],
                notes=f"{data['distance_km']} km · gas estimate",
            )
        ],
        total_duration_minutes=data["duration_minutes"],
        total_cost_usd=data["cost_usd"],
        transfers=0,
    )


async def _build_transit_only(
    origin: str,
    destination: str,
    departure_time: str,
    google_key: str,
) -> Optional[ComposedRoute]:
    data = await get_transit_route(origin, destination, departure_time, google_key)
    if not data:
        return None
    return ComposedRoute(
        route_type="transit_only",
        label="Public transit",
        segments=[
            RouteSegment(
                mode=TransportMode.TRANSIT,
                from_location=origin,
                to_location=destination,
                duration_minutes=data["duration_minutes"],
                cost_usd=data["cost_usd"],
                notes=None if data["cost_usd"] > 0 else "Fare unavailable for this route",
            )
        ],
        total_duration_minutes=data["duration_minutes"],
        total_cost_usd=data["cost_usd"],
        transfers=1,
    )


async def _build_one_fly_route(
    origin: str,
    destination: str,
    departure_time: str,
    flight: dict,
    google_key: str,
) -> Optional[ComposedRoute]:
    """Build a single drive+fly+transit/rideshare route for one flight offer."""
    orig_airport = flight["origin_airport_name"]
    dest_airport = flight["dest_airport_name"]
    orig_iata = flight["origin_iata"]
    dest_iata = flight["dest_iata"]

    # Fetch drive-to-airport and transit-from-airport in parallel
    drive_to, transit_from = await asyncio.gather(
        get_driving_route(origin, orig_airport, google_key),
        get_transit_route(dest_airport, destination, departure_time, google_key),
    )

    if not drive_to:
        return None

    segments: List[RouteSegment] = [
        RouteSegment(
            mode=TransportMode.DRIVE,
            from_location=origin,
            to_location=orig_airport,
            duration_minutes=drive_to["duration_minutes"],
            distance_km=drive_to["distance_km"],
            cost_usd=drive_to["cost_usd"],
        ),
        RouteSegment(
            mode=TransportMode.FLIGHT,
            from_location=orig_iata,
            to_location=dest_iata,
            duration_minutes=flight["duration_minutes"],
            cost_usd=flight["cost_usd"],
            carrier=flight["carrier"],
            departure_time=flight["departure_time"],
            arrival_time=flight["arrival_time"],
        ),
    ]

    last_leg_minutes = 0
    last_leg_cost = 0.0
    last_leg_mode = "transit"

    if transit_from and transit_from["duration_minutes"] > 0:
        segments.append(
            RouteSegment(
                mode=TransportMode.TRANSIT,
                from_location=dest_airport,
                to_location=destination,
                duration_minutes=transit_from["duration_minutes"],
                cost_usd=transit_from["cost_usd"],
            )
        )
        last_leg_minutes = transit_from["duration_minutes"]
        last_leg_cost = transit_from["cost_usd"]
    else:
        # Fall back to rideshare estimate using driving distance
        drive_from = await get_driving_route(dest_airport, destination, google_key)
        if drive_from:
            km = drive_from.get("distance_km", 20.0)
            rs_cost = round(km * _RIDESHARE_COST_PER_KM, 2)
            rs_minutes = round(km / _RIDESHARE_SPEED_KMH * 60)
            segments.append(
                RouteSegment(
                    mode=TransportMode.RIDESHARE,
                    from_location=dest_airport,
                    to_location=destination,
                    duration_minutes=rs_minutes,
                    cost_usd=rs_cost,
                    distance_km=km,
                    notes="Rideshare estimate",
                )
            )
            last_leg_minutes = rs_minutes
            last_leg_cost = rs_cost
            last_leg_mode = "rideshare"

    total_minutes = (
        drive_to["duration_minutes"]
        + _AIRPORT_OVERHEAD_MINUTES
        + flight["duration_minutes"]
        + last_leg_minutes
    )
    total_cost = round(drive_to["cost_usd"] + flight["cost_usd"] + last_leg_cost, 2)

    return ComposedRoute(
        route_type=f"drive_fly_{last_leg_mode}",
        label=f"Drive to {orig_iata} + Fly {orig_iata}→{dest_iata} + {last_leg_mode.capitalize()}",
        segments=segments,
        total_duration_minutes=total_minutes,
        total_cost_usd=total_cost,
        transfers=2,
    )


async def _build_fly_routes(
    origin: str,
    destination: str,
    departure_time: str,
    google_key: str,
    serpapi_key: str,
) -> List[ComposedRoute]:
    departure_date = departure_time[:10]  # YYYY-MM-DD

    flights = await search_flights(origin, destination, departure_date, serpapi_key)
    if not flights:
        logger.info("No flights found for %s → %s on %s", origin, destination, departure_date)
        return []

    # Build all fly-route variants concurrently
    tasks = [
        _build_one_fly_route(origin, destination, departure_time, flight, google_key)
        for flight in flights
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    routes = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Fly route builder raised: %s", result)
        elif result is not None:
            routes.append(result)

    return routes


def _score_and_tag(routes: List[ComposedRoute], preference: str) -> List[ComposedRoute]:
    if not routes:
        return routes

    max_cost = max(r.total_cost_usd for r in routes) or 1.0
    max_time = max(r.total_duration_minutes for r in routes) or 1.0

    if preference == "cheap":
        cost_w, time_w, transfer_w = 0.7, 0.2, 0.1
    elif preference == "fast":
        cost_w, time_w, transfer_w = 0.1, 0.8, 0.1
    else:  # balanced
        cost_w, time_w, transfer_w = 0.4, 0.4, 0.2

    for route in routes:
        norm_cost = route.total_cost_usd / max_cost
        norm_time = route.total_duration_minutes / max_time
        norm_transfers = route.transfers / 3
        route.score = round(
            cost_w * norm_cost + time_w * norm_time + transfer_w * norm_transfers, 4
        )

    routes.sort(key=lambda r: r.score or 0)

    # Tag standout routes
    cheapest = min(routes, key=lambda r: r.total_cost_usd)
    fastest = min(routes, key=lambda r: r.total_duration_minutes)
    cheapest.tags.append("cheapest")
    if fastest is not cheapest:
        fastest.tags.append("fastest")
    for route in routes:
        if not route.tags:
            route.tags.append("best_value")
            break

    return routes


async def compose_routes(
    request: SearchRequest,
    google_key: str,
    serpapi_key: str,
) -> List[ComposedRoute]:
    tasks = [
        _build_drive_only(request.origin, request.destination, google_key),
        _build_transit_only(
            request.origin, request.destination, request.departure_time, google_key
        ),
    ]

    if serpapi_key:
        tasks.append(
            _build_fly_routes(
                request.origin,
                request.destination,
                request.departure_time,
                google_key,
                serpapi_key,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    routes: List[ComposedRoute] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Route builder raised: %s", result)
        elif isinstance(result, list):
            routes.extend(result)
        elif result is not None:
            routes.append(result)

    return _score_and_tag(routes, request.preference)
