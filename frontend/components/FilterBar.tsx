'use client';

import { LayoutGrid, DollarSign, Zap, ArrowLeftRight } from 'lucide-react';
import { SortFilter } from '@/lib/types';

interface Props {
  value: SortFilter;
  onChange: (f: SortFilter) => void;
  count: number;
}

const OPTIONS: { value: SortFilter; label: string; Icon: React.ElementType }[] = [
  { value: 'all',       label: 'All',       Icon: LayoutGrid      },
  { value: 'cheap',     label: 'Cheapest',  Icon: DollarSign      },
  { value: 'fast',      label: 'Fastest',   Icon: Zap             },
  { value: 'transfers', label: 'Transfers', Icon: ArrowLeftRight   },
];

export default function FilterBar({ value, onChange, count }: Props) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-gray-400 font-semibold uppercase tracking-wide">
        {count} route{count !== 1 ? 's' : ''}
      </span>
      <div className="flex gap-1.5 flex-wrap">
        {OPTIONS.map(({ value: v, label, Icon }) => {
          const active = value === v;
          return (
            <button
              key={v}
              onClick={() => onChange(v)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                active
                  ? 'bg-sky-600 text-white border-sky-600 shadow-sm shadow-sky-200'
                  : 'bg-white text-gray-500 border-gray-200 hover:border-sky-300 hover:text-sky-600'
              }`}
            >
              <Icon className="w-3 h-3" />
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
