import { ComposedRoute, RouteSegment, TransportMode } from '@/lib/types';

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

function formatCost(usd: number): string {
  if (usd === 0) return 'Free / unknown';
  return `$${usd.toFixed(2)}`;
}

const MODE_CONFIG: Record<TransportMode, { icon: string; label: string; className: string }> = {
  drive:     { icon: '🚗', label: 'Drive',     className: 'bg-blue-50   text-blue-700   border-blue-100'   },
  transit:   { icon: '🚌', label: 'Transit',   className: 'bg-green-50  text-green-700  border-green-100'  },
  flight:    { icon: '✈️', label: 'Flight',    className: 'bg-purple-50 text-purple-700 border-purple-100' },
  walk:      { icon: '🚶', label: 'Walk',      className: 'bg-gray-50   text-gray-600   border-gray-100'   },
  rideshare: { icon: '🚕', label: 'Rideshare', className: 'bg-orange-50 text-orange-700 border-orange-100' },
};

const TAG_CONFIG: Record<string, { label: string; className: string }> = {
  cheapest:   { label: 'Cheapest',   className: 'bg-green-100  text-green-700'  },
  fastest:    { label: 'Fastest',    className: 'bg-blue-100   text-blue-700'   },
  best_value: { label: 'Best value', className: 'bg-purple-100 text-purple-700' },
};

function SegmentRow({ seg }: { seg: RouteSegment }) {
  const cfg = MODE_CONFIG[seg.mode];
  return (
    <div className="flex items-start gap-3 py-2.5">
      <span className={`shrink-0 text-xs font-medium px-2 py-1 rounded border ${cfg.className}`}>
        {cfg.icon} {cfg.label}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 truncate">
          {seg.from_location} → {seg.to_location}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {formatDuration(seg.duration_minutes)}
          {seg.cost_usd > 0 ? ` · ${formatCost(seg.cost_usd)}` : ''}
          {seg.carrier ? ` · ${seg.carrier}` : ''}
          {seg.distance_km ? ` · ${seg.distance_km} km` : ''}
          {seg.notes ? ` · ${seg.notes}` : ''}
        </p>
      </div>
    </div>
  );
}

interface Props {
  route: ComposedRoute;
  rank: number;
  isActive: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

export default function RouteCard({ route, rank, isActive, onMouseEnter, onMouseLeave }: Props) {
  const isTop = rank === 0;

  return (
    <div
      className={`bg-white rounded-2xl border overflow-hidden cursor-pointer transition-shadow ${
        isActive
          ? 'border-sky-400 shadow-lg ring-1 ring-sky-200'
          : isTop
          ? 'border-sky-200 shadow-md'
          : 'border-gray-100 shadow-sm hover:shadow-md'
      }`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Header */}
      <div className={`px-5 py-4 border-b ${isTop || isActive ? 'bg-sky-50 border-sky-100' : 'bg-gray-50 border-gray-100'}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">{route.label}</h3>
            {route.tags.length > 0 && (
              <div className="flex gap-1.5 mt-1.5 flex-wrap">
                {route.tags.map(tag => (
                  <span
                    key={tag}
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${TAG_CONFIG[tag]?.className ?? 'bg-gray-100 text-gray-600'}`}
                  >
                    {TAG_CONFIG[tag]?.label ?? tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-xl font-bold text-gray-900">{formatCost(route.total_cost_usd)}</p>
            <p className="text-sm text-gray-500">{formatDuration(route.total_duration_minutes)}</p>
          </div>
        </div>
      </div>

      {/* Segments */}
      <div className="px-5 divide-y divide-gray-50">
        {route.segments.map((seg, i) => <SegmentRow key={i} seg={seg} />)}
      </div>

      {route.transfers > 0 && (
        <div className="px-5 py-2 border-t border-gray-50">
          <p className="text-xs text-gray-400">{route.transfers} transfer{route.transfers > 1 ? 's' : ''}</p>
        </div>
      )}
    </div>
  );
}
