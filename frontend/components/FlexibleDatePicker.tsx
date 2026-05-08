'use client';

import { CalendarDays, Plane, Bus } from 'lucide-react';
import { DateOption } from '@/lib/types';

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function bestPrice(opt: DateOption): { price: number; mode: 'flight' | 'bus' } | null {
  if (opt.min_flight_usd !== null && opt.min_bus_usd !== null) {
    return opt.min_flight_usd <= opt.min_bus_usd
      ? { price: opt.min_flight_usd, mode: 'flight' }
      : { price: opt.min_bus_usd, mode: 'bus' };
  }
  if (opt.min_flight_usd !== null) return { price: opt.min_flight_usd, mode: 'flight' };
  if (opt.min_bus_usd !== null) return { price: opt.min_bus_usd, mode: 'bus' };
  return null;
}

interface Props {
  dates: DateOption[];
  selectedDate: string;   // YYYY-MM-DD
  onSelect: (date: string) => void;
  loading: boolean;
}

export default function FlexibleDatePicker({ dates, selectedDate, onSelect, loading }: Props) {
  const today = new Date().toISOString().split('T')[0];

  // Find cheapest date (by best available price)
  let cheapestDate: string | null = null;
  let cheapestPrice = Infinity;
  for (const opt of dates) {
    const b = bestPrice(opt);
    if (b && b.price < cheapestPrice) {
      cheapestPrice = b.price;
      cheapestDate = opt.date;
    }
  }

  return (
    <div className="mt-6 p-4 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <CalendarDays className="w-4 h-4 text-sky-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Flexible dates — cheapest options nearby
        </span>
      </div>

      {loading ? (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {Array.from({ length: 7 }).map((_, i) => (
            <div
              key={i}
              className="shrink-0 w-20 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {dates.map(opt => {
            const d = new Date(opt.date + 'T12:00:00'); // noon to avoid TZ edge cases
            const isSelected = opt.date === selectedDate;
            const isCheapest = opt.date === cheapestDate;
            const isPast = opt.date < today;
            const best = bestPrice(opt);
            const dayName = DAY_NAMES[d.getDay()];
            const dateLabel = `${MONTH_NAMES[d.getMonth()]} ${d.getDate()}`;

            return (
              <button
                key={opt.date}
                disabled={isPast}
                onClick={() => !isPast && onSelect(opt.date)}
                className={`shrink-0 w-[4.75rem] rounded-xl border px-2 py-2.5 flex flex-col items-center gap-0.5 transition-all text-center ${
                  isSelected
                    ? 'bg-sky-600 border-sky-600 text-white shadow-md shadow-sky-200 dark:shadow-none'
                    : isPast
                    ? 'bg-gray-50 dark:bg-gray-800/50 border-gray-100 dark:border-gray-800 text-gray-300 dark:text-gray-600 cursor-not-allowed'
                    : isCheapest
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 hover:border-emerald-400'
                    : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-sky-300 dark:hover:border-sky-700'
                }`}
              >
                <span className={`text-[10px] font-semibold uppercase tracking-wide ${isSelected ? 'text-sky-100' : 'opacity-60'}`}>
                  {dayName}
                </span>
                <span className="text-xs font-bold">{dateLabel}</span>

                {best ? (
                  <span className={`flex items-center gap-0.5 text-[10px] font-semibold mt-0.5 ${
                    isSelected ? 'text-sky-100' : isCheapest ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {best.mode === 'flight'
                      ? <Plane className="w-2.5 h-2.5" />
                      : <Bus className="w-2.5 h-2.5" />
                    }
                    ${Math.round(best.price)}
                  </span>
                ) : (
                  <span className="text-[10px] text-gray-300 dark:text-gray-600 mt-0.5">—</span>
                )}

                {isCheapest && !isSelected && (
                  <span className="text-[9px] font-bold text-emerald-600 dark:text-emerald-400 leading-none">
                    Best
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
