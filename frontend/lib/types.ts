export type TransportMode = 'drive' | 'transit' | 'flight' | 'walk' | 'rideshare';
export type Preference = 'cheap' | 'fast' | 'balanced';

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
  departure_time: string; // ISO 8601
  preference: Preference;
}

export interface SearchResponse {
  routes: ComposedRoute[];
  search_id: string;
}
