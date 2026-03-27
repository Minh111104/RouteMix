export type TransportMode = 'drive' | 'transit' | 'flight' | 'walk' | 'rideshare';
export type Preference = 'cheap' | 'fast' | 'balanced';
export type SortFilter = 'all' | 'cheap' | 'fast' | 'transfers';

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
}

export interface SearchRequest {
  origin: string;
  destination: string;
  departure_time: string;
  preference: Preference;
}

export interface SearchResponse {
  routes: ComposedRoute[];
  search_id: string;
}
