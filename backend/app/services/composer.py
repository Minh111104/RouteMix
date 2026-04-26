import asyncio
import logging
from typing import List, Optional, Tuple

from app.models.route import ComposedRoute, Coords, RouteSegment, SearchRequest, TransportMode
from app.services.airports import find_nearest_airports
from app.services.amtrak import estimate_train
from app.services.flixbus import search_buses
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
    data: Optional[dict],
    origin: str,
    destination: str,
    origin_coords: Optional[Tuple[float, float]],
    dest_coords: Optional[Tuple[float, float]],
) -> Optional[ComposedRoute]:
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


async def _build_train_only(
    data: Optional[dict],
    origin: str,
    destination: str,
    origin_coords: Optional[Tuple[float, float]],
    dest_coords: Optional[Tuple[float, float]],
) -> Optional[ComposedRoute]:
    """Amtrak estimate using haversine distance and corridor-aware pricing."""
    if not origin_coords or not dest_coords:
        return None
    result = estimate_train(origin_coords, dest_coords)
    if not result:
        return None
    return ComposedRoute(
        route_type="train_only",
        label="Train (Amtrak)",
        segments=[
            RouteSegment(
                mode=TransportMode.TRAIN,
                from_location=origin,
                to_location=destination,
                duration_minutes=result["duration_minutes"],
                distance_km=result["distance_km"],
                cost_usd=result["cost_usd"],
                notes=f"Amtrak estimate · {result['corridor']}",
                from_coords=_coords(origin_coords),
                to_coords=_coords(dest_coords),
                polyline=data.get("polyline") if data else None,
            )
        ],
        total_duration_minutes=result["duration_minutes"],
        total_cost_usd=result["cost_usd"],
        transfers=0,
    )


async def _build_bus_only(
    data: Optional[dict],
    origin: str,
    destination: str,
    origin_coords: Optional[Tuple[float, float]],
    dest_coords: Optional[Tuple[float, float]],
    departure_time: str,
) -> Optional[ComposedRoute]:
    """Try FlixBus live data; fall back to distance-based estimate."""
    departure_date = departure_time[:10]
    fb = await search_buses(origin, destination, departure_date)

    if fb:
        notes = f"FlixBus · departs {fb['departure_time'][:16] if fb.get('departure_time') else departure_date}"
        return ComposedRoute(
            route_type="bus_only",
            label="Intercity bus (FlixBus)",
            segments=[
                RouteSegment(
                    mode=TransportMode.BUS,
                    from_location=origin,
                    to_location=destination,
                    duration_minutes=fb["duration_minutes"],
                    distance_km=data["distance_km"] if data else None,
                    cost_usd=fb["cost_usd"],
                    carrier=fb["carrier"],
                    departure_time=fb.get("departure_time"),
                    arrival_time=fb.get("arrival_time"),
                    notes=notes,
                    from_coords=_coords(origin_coords),
                    to_coords=_coords(dest_coords),
                    polyline=data.get("polyline") if data else None,
                )
            ],
            total_duration_minutes=fb["duration_minutes"],
            total_cost_usd=fb["cost_usd"],
            transfers=0,
        )

    # FlixBus unavailable — fall back to estimate
    if not data:
        return None
    km = data["distance_km"]
    if km < 100:
        return None
    duration = round(km / 70 * 60)
    cost = round(km * 0.07, 2)
    return ComposedRoute(
        route_type="bus_only",
        label="Intercity bus",
        segments=[
            RouteSegment(
                mode=TransportMode.BUS,
                from_location=origin,
                to_location=destination,
                duration_minutes=duration,
                distance_km=km,
                cost_usd=cost,
                notes="Estimate · e.g. Greyhound / FlixBus",
                from_coords=_coords(origin_coords),
                to_coords=_coords(dest_coords),
                polyline=data.get("polyline"),
            )
        ],
        total_duration_minutes=duration,
        total_cost_usd=cost,
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
                polyline=data.get("polyline"),
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
                    polyline=drive_from.get("polyline"),
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


async def _build_multistop_drive(
    cities: List[str],
    pairs: List[tuple],
    drive_legs: List[Optional[dict]],
    coords_map: dict,
) -> Optional[ComposedRoute]:
    if any(leg is None for leg in drive_legs):
        return None
    segments = [
        RouteSegment(
            mode=TransportMode.DRIVE,
            from_location=a,
            to_location=b,
            duration_minutes=leg["duration_minutes"],
            distance_km=leg["distance_km"],
            cost_usd=leg["cost_usd"],
            notes=f"{leg['distance_km']} km · gas estimate",
            from_coords=_coords(coords_map.get(a)),
            to_coords=_coords(coords_map.get(b)),
            polyline=leg.get("polyline"),
        )
        for (a, b), leg in zip(pairs, drive_legs)
    ]
    n = len(pairs)
    return ComposedRoute(
        route_type="drive_only",
        label=f"Drive · {n} leg{'s' if n > 1 else ''}",
        segments=segments,
        total_duration_minutes=sum(s.duration_minutes for s in segments),
        total_cost_usd=round(sum(s.cost_usd for s in segments), 2),
        transfers=0,
    )


async def _build_multistop_train(
    cities: List[str],
    pairs: List[tuple],
    coords_map: dict,
    drive_legs: List[Optional[dict]],
) -> Optional[ComposedRoute]:
    segments = []
    for i, (a, b) in enumerate(pairs):
        a_coords = coords_map.get(a)
        b_coords = coords_map.get(b)
        if not a_coords or not b_coords:
            return None
        result = estimate_train(a_coords, b_coords)
        if not result:
            return None
        segments.append(RouteSegment(
            mode=TransportMode.TRAIN,
            from_location=a,
            to_location=b,
            duration_minutes=result["duration_minutes"],
            distance_km=result["distance_km"],
            cost_usd=result["cost_usd"],
            notes=f"Amtrak estimate · {result['corridor']}",
            from_coords=_coords(a_coords),
            to_coords=_coords(b_coords),
            polyline=drive_legs[i].get("polyline") if drive_legs[i] else None,
        ))
    n = len(pairs)
    return ComposedRoute(
        route_type="train_only",
        label=f"Train · {n} leg{'s' if n > 1 else ''}",
        segments=segments,
        total_duration_minutes=sum(s.duration_minutes for s in segments),
        total_cost_usd=round(sum(s.cost_usd for s in segments), 2),
        transfers=len(pairs) - 1,
    )


async def _build_multistop_bus(
    cities: List[str],
    pairs: List[tuple],
    coords_map: dict,
    drive_legs: List[Optional[dict]],
    departure_time: str,
) -> Optional[ComposedRoute]:
    departure_date = departure_time[:10]
    fb_results = await asyncio.gather(
        *[search_buses(a, b, departure_date) for a, b in pairs],
        return_exceptions=True,
    )
    segments = []
    for i, (a, b) in enumerate(pairs):
        fb = fb_results[i] if not isinstance(fb_results[i], Exception) else None
        dl = drive_legs[i]
        if fb:
            segments.append(RouteSegment(
                mode=TransportMode.BUS,
                from_location=a,
                to_location=b,
                duration_minutes=fb["duration_minutes"],
                distance_km=dl["distance_km"] if dl else None,
                cost_usd=fb["cost_usd"],
                carrier=fb["carrier"],
                departure_time=fb.get("departure_time"),
                arrival_time=fb.get("arrival_time"),
                notes="FlixBus · live fare",
                from_coords=_coords(coords_map.get(a)),
                to_coords=_coords(coords_map.get(b)),
                polyline=dl.get("polyline") if dl else None,
            ))
        elif dl and dl["distance_km"] >= 100:
            km = dl["distance_km"]
            segments.append(RouteSegment(
                mode=TransportMode.BUS,
                from_location=a,
                to_location=b,
                duration_minutes=round(km / 70 * 60),
                distance_km=km,
                cost_usd=round(km * 0.07, 2),
                notes="Estimate · e.g. Greyhound / FlixBus",
                from_coords=_coords(coords_map.get(a)),
                to_coords=_coords(coords_map.get(b)),
                polyline=dl.get("polyline"),
            ))
        else:
            return None
    n = len(pairs)
    return ComposedRoute(
        route_type="bus_only",
        label=f"Bus · {n} leg{'s' if n > 1 else ''}",
        segments=segments,
        total_duration_minutes=sum(s.duration_minutes for s in segments),
        total_cost_usd=round(sum(s.cost_usd for s in segments), 2),
        transfers=len(pairs) - 1,
    )


async def _compose_multistop(
    cities: List[str],
    request: "SearchRequest",
    google_key: str,
    serpapi_key: str,
) -> List[ComposedRoute]:
    pairs = list(zip(cities, cities[1:]))

    geocode_results, drive_results = await asyncio.gather(
        asyncio.gather(*[geocode_address(c, google_key) for c in cities], return_exceptions=True),
        asyncio.gather(*[get_driving_route(a, b, google_key) for a, b in pairs], return_exceptions=True),
    )

    coords_map = {
        city: (None if isinstance(r, Exception) else r)
        for city, r in zip(cities, geocode_results)
    }
    drive_legs = [None if isinstance(r, Exception) else r for r in drive_results]

    results = await asyncio.gather(
        _build_multistop_drive(cities, pairs, drive_legs, coords_map),
        _build_multistop_train(cities, pairs, coords_map, drive_legs),
        _build_multistop_bus(cities, pairs, coords_map, drive_legs, request.departure_time),
        return_exceptions=True,
    )

    routes: List[ComposedRoute] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Multi-stop builder raised: %s", result)
        elif result is not None:
            routes.append(result)

    return _score_and_tag(routes, request.preference)


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
    waypoints = [w.strip() for w in (request.waypoints or []) if w.strip()]
    if waypoints:
        cities = [request.origin, *waypoints, request.destination]
        return await _compose_multistop(cities, request, google_key, serpapi_key)

    # Geocode + fetch driving route once — reused by drive/train/bus builders
    origin_coords, dest_coords, driving_data = await asyncio.gather(
        geocode_address(request.origin, google_key),
        geocode_address(request.destination, google_key),
        get_driving_route(request.origin, request.destination, google_key),
    )

    tasks = [
        _build_drive_only(
            driving_data, request.origin, request.destination, origin_coords, dest_coords,
        ),
        _build_transit_only(
            request.origin, request.destination, request.departure_time,
            origin_coords, dest_coords, google_key,
        ),
        _build_train_only(
            driving_data, request.origin, request.destination, origin_coords, dest_coords,
        ),
        _build_bus_only(
            driving_data, request.origin, request.destination, origin_coords, dest_coords,
            request.departure_time,
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
