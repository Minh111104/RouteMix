'use client';

import { SortFilter } from '@/lib/types';

interface Props {
  value: SortFilter;
  onChange: (f: SortFilter) => void;
  count: number;
}

const OPTIONS: { value: SortFilter; label: string }[] = [
  { value: 'all', label: 'All routes' },
  { value: 'cheap', label: 'Cheapest first' },
  { value: 'fast', label: 'Fastest first' },
  { value: 'transfers', label: 'Fewest transfers' },
];

export default function FilterBar({ value, onChange, count }: Props) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-gray-400 font-medium uppercase tracking-wide mr-1">
        {count} route{count !== 1 ? 's' : ''}
      </span>
      {OPTIONS.map(opt => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
            value === opt.value
              ? 'bg-gray-900 text-white border-gray-900'
              : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
