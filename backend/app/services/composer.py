import asyncio
import logging
from typing import List, Optional, Tuple

from app.models.route import ComposedRoute, Coords, RouteSegment, SearchRequest, TransportMode
from app.services.airports import find_nearest_airports
from app.services.google_routes import geocode_address, get_driving_route, get_transit_route
from app.services.serpapi import search_flights

logger = logging.getLogger(__name__)

_RIDESHARE_COST_PER_KM = 1.50
_RIDESHARE_SPEED_KMH = 40
_AIRPORT_OVERHEAD_MINUTES = 90


def _coords(pair: Optional[Tuple[float, float]]) -> Optional[Coords]:
    return Coords(lat=pair[0], lon=pair[1]) if pair else None


def _ap_coords(ap: dict) -> Coords:
    return Coords(lat=ap["lat"], lon=ap["lon"])


async def _build_drive_only(
    origin: str,
    destination: str,
    origin_coords: Optional[Tuple[float, float]],
    dest_coords: Optional[Tuple[float, float]],
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
                from_coords=_coords(origin_coords),
                to_coords=_coords(dest_coords),
                polyline=data.get("polyline"),
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
    origin_coords: Optional[Tuple[float, float]],
    dest_coords: Optional[Tuple[float, float]],
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
                from_coords=_coords(origin_coords),
                to_coords=_coords(dest_coords),
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
    orig_ap: dict,
    dest_ap: dict,
    origin_coords: Optional[Tuple[float, float]],
    dest_coords: Optional[Tuple[float, float]],
    google_key: str,
) -> Optional[ComposedRoute]:
    orig_ap_address = f"{orig_ap['name']}, {orig_ap['city']}"
    dest_ap_address = f"{dest_ap['name']}, {dest_ap['city']}"

    # Airport coordinates come from local airportsdata — no geocoding needed
    orig_ap_c = _ap_coords(orig_ap)
    dest_ap_c = _ap_coords(dest_ap)

    # Fetch drive-to-airport and transit-from-airport in parallel
    drive_to, transit_from = await asyncio.gather(
        get_driving_route(origin, orig_ap_address, google_key),
        get_transit_route(dest_ap_address, destination, departure_time, google_key),
    )

    if not drive_to:
        return None

    segments: List[RouteSegment] = [
        RouteSegment(
            mode=TransportMode.DRIVE,
            from_location=origin,
            to_location=orig_ap_address,
            duration_minutes=drive_to["duration_minutes"],
            distance_km=drive_to["distance_km"],
            cost_usd=drive_to["cost_usd"],
            from_coords=_coords(origin_coords),
            to_coords=orig_ap_c,
            polyline=drive_to.get("polyline"),
        ),
        RouteSegment(
            mode=TransportMode.FLIGHT,
            from_location=orig_ap["iata"],
            to_location=dest_ap["iata"],
            duration_minutes=flight["duration_minutes"],
            cost_usd=flight["cost_usd"],
            carrier=flight["carrier"],
            departure_time=flight["departure_time"],
            arrival_time=flight["arrival_time"],
            from_coords=orig_ap_c,
            to_coords=dest_ap_c,
        ),
    ]

    last_leg_minutes = 0
    last_leg_cost = 0.0
    last_leg_mode = "transit"

    if transit_from and transit_from["duration_minutes"] > 0:
        segments.append(
            RouteSegment(
                mode=TransportMode.TRANSIT,
                from_location=dest_ap_address,
                to_location=destination,
                duration_minutes=transit_from["duration_minutes"],
                cost_usd=transit_from["cost_usd"],
                from_coords=dest_ap_c,
                to_coords=_coords(dest_coords),
            )
        )
        last_leg_minutes = transit_from["duration_minutes"]
        last_leg_cost = transit_from["cost_usd"]
    else:
        drive_from = await get_driving_route(dest_ap_address, destination, google_key)
        if drive_from:
            km = drive_from.get("distance_km", 20.0)
            rs_cost = round(km * _RIDESHARE_COST_PER_KM, 2)
            rs_minutes = round(km / _RIDESHARE_SPEED_KMH * 60)
            segments.append(
                RouteSegment(
                    mode=TransportMode.RIDESHARE,
                    from_location=dest_ap_address,
                    to_location=destination,
                    duration_minutes=rs_minutes,
                    cost_usd=rs_cost,
                    distance_km=km,
                    notes="Rideshare estimate",
                    from_coords=dest_ap_c,
                    to_coords=_coords(dest_coords),
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
    orig_iata = orig_ap["iata"]
    dest_iata = dest_ap["iata"]

    return ComposedRoute(
        route_type=f"drive_fly_{last_leg_mode}_{orig_iata}_{dest_iata}",
        label=f"Drive to {orig_iata} · Fly {orig_iata}→{dest_iata} · {last_leg_mode.capitalize()}",
        segments=segments,
        total_duration_minutes=total_minutes,
        total_cost_usd=total_cost,
        transfers=2,
    )


async def _build_fly_routes(
    origin: str,
    destination: str,
    departure_time: str,
    origin_coords: Tuple[float, float],
    dest_coords: Tuple[float, float],
    google_key: str,
    serpapi_key: str,
) -> List[ComposedRoute]:
    # commercial_only=True filters out GA airports by name pattern so we don't
    # waste Serpapi calls on TDZ/FDY/ADG-style airports.
    # max_results=6 ensures major hubs further out (e.g. DTW at 99km) are included.
    origin_airports = find_nearest_airports(
        origin_coords[0], origin_coords[1], max_results=6, commercial_only=True
    )
    dest_airports = find_nearest_airports(
        dest_coords[0], dest_coords[1], max_results=3, commercial_only=True
    )

    if not origin_airports or not dest_airports:
        logger.info("No airports found near origin or destination")
        return []

    logger.info(
        "Nearest origin airports: %s | Nearest dest airports: %s",
        [f"{a['iata']}({a['distance_km']}km)" for a in origin_airports],
        [f"{a['iata']}({a['distance_km']}km)" for a in dest_airports],
    )

    departure_date = departure_time[:10]
    routes: List[ComposedRoute] = []
    MAX_FLY_ROUTES = 2  # cap to limit Serpapi usage

    # Walk origin airports outward (small → major hub) until we have enough routes
    for orig_ap in origin_airports:
        if len(routes) >= MAX_FLY_ROUTES:
            break

        # Search this origin against all dest airports in parallel
        flight_results = await asyncio.gather(
            *[
                search_flights(orig_ap["iata"], dest_ap["iata"], departure_date, serpapi_key)
                for dest_ap in dest_airports
                if dest_ap["iata"] != orig_ap["iata"]
            ],
            return_exceptions=True,
        )

        for dest_ap, flights in zip(dest_airports, flight_results):
            if dest_ap["iata"] == orig_ap["iata"]:
                continue
            if isinstance(flights, Exception) or not flights:
                continue

            flight = min(flights, key=lambda f: f["cost_usd"])
            result = await _build_one_fly_route(
                origin, destination, departure_time,
                flight, orig_ap, dest_ap,
                origin_coords, dest_coords,
                google_key,
            )
            if result:
                routes.append(result)
                break  # found a working dest for this origin; move to next origin

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
    else:
        cost_w, time_w, transfer_w = 0.4, 0.4, 0.2

    for route in routes:
        route.score = round(
            cost_w * (route.total_cost_usd / max_cost)
            + time_w * (route.total_duration_minutes / max_time)
            + transfer_w * (route.transfers / 3),
            4,
        )

    routes.sort(key=lambda r: r.score or 0)

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
    # Geocode origin and destination once — used for map coords and airport search
    origin_coords, dest_coords = await asyncio.gather(
        geocode_address(request.origin, google_key),
        geocode_address(request.destination, google_key),
    )

    tasks = [
        _build_drive_only(
            request.origin, request.destination, origin_coords, dest_coords, google_key
        ),
        _build_transit_only(
            request.origin, request.destination, request.departure_time,
            origin_coords, dest_coords, google_key,
        ),
    ]

    if serpapi_key and origin_coords and dest_coords:
        tasks.append(
            _build_fly_routes(
                request.origin, request.destination, request.departure_time,
                origin_coords, dest_coords, google_key, serpapi_key,
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
