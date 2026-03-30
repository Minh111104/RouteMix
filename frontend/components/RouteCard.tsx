import { Car, Bus, Plane, Navigation, PersonStanding } from 'lucide-react';
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

const MODE_CONFIG: Record<
  TransportMode,
  { Icon: React.ElementType; label: string; pill: string; dot: string }
> = {
  drive:     { Icon: Car,           label: 'Drive',     pill: 'bg-blue-50 text-blue-700 border-blue-100',     dot: 'bg-blue-500'   },
  transit:   { Icon: Bus,           label: 'Transit',   pill: 'bg-green-50 text-green-700 border-green-100',  dot: 'bg-green-500'  },
  flight:    { Icon: Plane,         label: 'Flight',    pill: 'bg-purple-50 text-purple-700 border-purple-100', dot: 'bg-purple-500' },
  walk:      { Icon: PersonStanding,label: 'Walk',      pill: 'bg-gray-50 text-gray-600 border-gray-200',     dot: 'bg-gray-400'   },
  rideshare: { Icon: Navigation,    label: 'Rideshare', pill: 'bg-orange-50 text-orange-700 border-orange-100', dot: 'bg-orange-500' },
};

const TAG_CONFIG: Record<string, { label: string; className: string }> = {
  cheapest:   { label: 'Cheapest',   className: 'bg-green-100 text-green-700'  },
  fastest:    { label: 'Fastest',    className: 'bg-blue-100 text-blue-700'    },
  best_value: { label: 'Best value', className: 'bg-purple-100 text-purple-700' },
};

function SegmentRow({ seg, isLast }: { seg: RouteSegment; isLast: boolean }) {
  const cfg = MODE_CONFIG[seg.mode];
  const { Icon } = cfg;
  return (
    <div className="flex gap-3">
      {/* Timeline */}
      <div className="flex flex-col items-center shrink-0 pt-1">
        <div className={`w-7 h-7 rounded-full ${cfg.dot} flex items-center justify-center shadow-sm`}>
          <Icon className="w-3.5 h-3.5 text-white" />
        </div>
        {!isLast && <div className="w-px flex-1 bg-gray-100 my-1" />}
      </div>

      {/* Content */}
      <div className={`flex-1 min-w-0 ${isLast ? 'pb-0' : 'pb-3'}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${cfg.pill}`}>
            {cfg.label}
          </span>
          {seg.carrier && (
            <span className="text-xs text-gray-400">{seg.carrier}</span>
          )}
        </div>
        <p className="text-sm text-gray-700 mt-0.5 truncate">
          {seg.from_location} → {seg.to_location}
        </p>
        <p className="text-xs text-gray-400 mt-0.5 flex flex-wrap gap-x-2">
          <span>{formatDuration(seg.duration_minutes)}</span>
          {seg.cost_usd > 0 && <span>{formatCost(seg.cost_usd)}</span>}
          {seg.distance_km && <span>{seg.distance_km} km</span>}
          {seg.departure_time && <span>{seg.departure_time}</span>}
          {seg.notes && <span className="text-gray-300">{seg.notes}</span>}
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
      className={`bg-white rounded-2xl border overflow-hidden cursor-pointer transition-all duration-150 ${
        isActive
          ? 'border-sky-400 shadow-lg ring-2 ring-sky-100'
          : isTop
          ? 'border-sky-200 shadow-md'
          : 'border-gray-100 shadow-sm hover:shadow-md hover:border-gray-200'
      }`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Header */}
      <div className={`px-5 py-4 border-b ${isTop || isActive ? 'bg-gradient-to-r from-sky-50 to-indigo-50 border-sky-100' : 'bg-gray-50 border-gray-100'}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {isTop && (
                <span className="text-xs font-bold text-sky-600 bg-sky-100 px-2 py-0.5 rounded-full">#1</span>
              )}
              <h3 className="font-semibold text-gray-900 truncate">{route.label}</h3>
            </div>
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
            <p className="text-2xl font-extrabold text-gray-900 leading-none">
              {route.total_cost_usd > 0 ? `$${Math.round(route.total_cost_usd)}` : '—'}
            </p>
            <p className="text-xs text-gray-400 mt-1">{formatDuration(route.total_duration_minutes)}</p>
            {route.transfers > 0 && (
              <p className="text-xs text-gray-400">{route.transfers} transfer{route.transfers > 1 ? 's' : ''}</p>
            )}
          </div>
        </div>
      </div>

      {/* Segments timeline */}
      <div className="px-5 pt-4 pb-3">
        {route.segments.map((seg, i) => (
          <SegmentRow key={i} seg={seg} isLast={i === route.segments.length - 1} />
        ))}
      </div>
    </div>
  );
}
