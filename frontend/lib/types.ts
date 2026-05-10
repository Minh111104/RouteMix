export type TransportMode = 'drive' | 'transit' | 'flight' | 'walk' | 'rideshare' | 'train' | 'bus';
export type Preference = 'cheap' | 'fast' | 'balanced';
export type SortFilter = 'all' | 'cheap' | 'fast' | 'transfers' | 'eco';

export interface Coords {
  lat: number;
  lon: number;
}

export interface RouteSegment {
  mode: TransportMode;
  from_location: string;
  to_location: string;
  duration_minutes: number;
  cost_usd: number;
  distance_km?: number;
  carrier?: string;
  departure_time?: string;
  arrival_time?: string;
  notes?: string;
  from_coords?: Coords;
  to_coords?: Coords;
  polyline?: string;
  co2_kg?: number;
}

export interface ComposedRoute {
  route_type: string;
  label: string;
  segments: RouteSegment[];
  total_duration_minutes: number;
  total_cost_usd: number;
  transfers: number;
  score?: number;
  tags: string[];
  total_co2_kg?: number;
}

export interface SearchRequest {
  origin: string;
  destination: string;
  waypoints?: string[];
  departure_time: string;
  preference: Preference;
}

export interface SearchResponse {
  routes: ComposedRoute[];
  recommendation?: string;
  search_id: string;
}

export interface DateOption {
  date: string;           // YYYY-MM-DD
  min_flight_usd: number | null;
  min_bus_usd: number | null;
}

export interface FlexibleDatesResponse {
  dates: DateOption[];
  origin_iata: string | null;
  dest_iata: string | null;
}
