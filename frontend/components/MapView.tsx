'use client';

// This component is loaded with { ssr: false } so Leaflet runs only on the client.
import { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { ComposedRoute, TransportMode } from '@/lib/types';

/** Decode a Google Maps encoded polyline string into [lat, lng] pairs. */
function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let b: number;
    let shift = 0;
    let result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;

    points.push([lat / 1e5, lng / 1e5]);
  }

  return points;
}

const MODE_COLORS: Record<TransportMode, string> = {
  drive:     '#3b82f6', // blue
  transit:   '#22c55e', // green
  flight:    '#a855f7', // purple
  rideshare: '#f97316', // orange
  walk:      '#6b7280', // gray
  train:     '#0d9488', // teal
  bus:       '#d97706', // amber
};

function AutoFit({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length >= 2) {
      map.fitBounds(points, { padding: [48, 48], maxZoom: 13 });
    }
  // Stringify so the effect only re-runs when actual coordinates change
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(points)]);
  return null;
}

interface Props {
  routes: ComposedRoute[];
  activeRouteType: string | null;       // highlighted by hover
  onRouteClick: (type: string) => void;
}

export default function MapView({ routes, activeRouteType, onRouteClick }: Props) {
  // Collect all unique coordinate points across all routes for auto-fit
  const allPoints: [number, number][] = [];
  const seen = new Set<string>();
  routes.forEach(route =>
    route.segments.forEach(seg => {
      if (seg.polyline) {
        decodePolyline(seg.polyline).forEach(([lat, lng]) => {
          const key = `${lat.toFixed(4)},${lng.toFixed(4)}`;
          if (!seen.has(key)) { seen.add(key); allPoints.push([lat, lng]); }
        });
      } else {
        for (const coords of [seg.from_coords, seg.to_coords]) {
          if (!coords) continue;
          const key = `${coords.lat},${coords.lon}`;
          if (!seen.has(key)) { seen.add(key); allPoints.push([coords.lat, coords.lon]); }
        }
      }
    })
  );

  // Find origin (first from_coords) and destination (last to_coords) for markers
  let originPoint: [number, number] | null = null;
  let destPoint: [number, number] | null = null;
  for (const route of routes) {
    if (!originPoint && route.segments[0]?.from_coords) {
      const c = route.segments[0].from_coords;
      originPoint = [c.lat, c.lon];
    }
    const last = route.segments[route.segments.length - 1];
    if (!destPoint && last?.to_coords) {
      const c = last.to_coords;
      destPoint = [c.lat, c.lon];
    }
    if (originPoint && destPoint) break;
  }

  return (
    <MapContainer
      center={[39.5, -98.35]}
      zoom={4}
      style={{ height: '100%', width: '100%', borderRadius: '0.75rem' }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />

      {allPoints.length >= 2 && <AutoFit points={allPoints} />}

      {/* Route polylines */}
      {routes.map(route =>
        route.segments.map((seg, si) => {
          const color = MODE_COLORS[seg.mode] ?? '#6b7280';
          const isActive = route.route_type === activeRouteType;
          const isDimmed = activeRouteType !== null && !isActive;
          const pathOptions = {
            color,
            weight: isActive ? 6 : 3,
            opacity: isDimmed ? 0.2 : isActive ? 1 : 0.65,
            dashArray: seg.mode === 'flight' ? '10 6' : undefined,
          };

          // Drive segments: render actual route shape from encoded polyline
          if (seg.polyline) {
            return (
              <Polyline
                key={`${route.route_type}-${si}`}
                positions={decodePolyline(seg.polyline)}
                pathOptions={pathOptions}
                eventHandlers={{ click: () => onRouteClick(route.route_type) }}
              />
            );
          }

          // Flight / rideshare / transit: straight line between endpoints
          if (!seg.from_coords || !seg.to_coords) return null;
          const from: [number, number] = [seg.from_coords.lat, seg.from_coords.lon];
          const to: [number, number] = [seg.to_coords.lat, seg.to_coords.lon];
          return (
            <Polyline
              key={`${route.route_type}-${si}`}
              positions={[from, to]}
              pathOptions={pathOptions}
              eventHandlers={{ click: () => onRouteClick(route.route_type) }}
            />
          );
        })
      )}

      {/* Origin marker */}
      {originPoint && (
        <CircleMarker
          center={originPoint}
          radius={8}
          pathOptions={{ color: '#1d4ed8', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
        >
          <Tooltip permanent direction="top" offset={[0, -10]}>Origin</Tooltip>
        </CircleMarker>
      )}

      {/* Destination marker */}
      {destPoint && (
        <CircleMarker
          center={destPoint}
          radius={8}
          pathOptions={{ color: '#15803d', fillColor: '#22c55e', fillOpacity: 1, weight: 2 }}
        >
          <Tooltip permanent direction="top" offset={[0, -10]}>Destination</Tooltip>
        </CircleMarker>
      )}
    </MapContainer>
  );
}
