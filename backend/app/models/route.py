from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid


class TransportMode(str, Enum):
    DRIVE = "drive"
    TRANSIT = "transit"
    FLIGHT = "flight"
    WALK = "walk"
    RIDESHARE = "rideshare"


class Preference(str, Enum):
    CHEAP = "cheap"
    FAST = "fast"
    BALANCED = "balanced"


class Coords(BaseModel):
    lat: float
    lon: float


class RouteSegment(BaseModel):
    mode: TransportMode
    from_location: str
    to_location: str
    duration_minutes: int
    cost_usd: float
    distance_km: Optional[float] = None
    carrier: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    notes: Optional[str] = None
    from_coords: Optional[Coords] = None
    to_coords: Optional[Coords] = None


class ComposedRoute(BaseModel):
    route_type: str
    label: str
    segments: List[RouteSegment]
    total_duration_minutes: int
    total_cost_usd: float
    transfers: int
    score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    origin: str
    destination: str
    departure_time: str  # ISO 8601, e.g. "2024-01-15T09:00:00"
    preference: Preference = Preference.BALANCED


class SearchResponse(BaseModel):
    routes: List[ComposedRoute]
    search_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
