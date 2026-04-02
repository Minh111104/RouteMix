'use client';

import { useState } from 'react';
import { MapPin, Calendar, Clock, ArrowLeftRight, Search, Loader2 } from 'lucide-react';
import { SearchRequest } from '@/lib/types';

interface Props {
  onSearch: (req: SearchRequest) => void;
  loading: boolean;
}

export default function SearchForm({ onSearch, loading }: Props) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('09:00');

  const today = new Date().toISOString().split('T')[0];

  function handleSwap() {
    setOrigin(destination);
    setDestination(origin);
  }

  function handleSubmit(e: { preventDefault(): void }) {
    e.preventDefault();
    onSearch({ origin, destination, departure_time: `${date}T${time}:00`, preference: 'balanced' });
  }

  const inputClass =
    'w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 placeholder-gray-300 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent text-sm';

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-800 p-5"
    >
      <div className="flex flex-wrap gap-3 items-end">
        {/* Origin */}
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">From</label>
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-400" />
            <input
              type="text"
              value={origin}
              onChange={e => setOrigin(e.target.value)}
              placeholder="City or address"
              required
              className={inputClass}
            />
          </div>
        </div>

        {/* Swap button */}
        <button
          type="button"
          onClick={handleSwap}
          className="p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 hover:text-sky-600 hover:border-sky-300 hover:bg-sky-50 dark:hover:bg-sky-900/20 transition-colors"
          title="Swap origin and destination"
        >
          <ArrowLeftRight className="w-4 h-4" />
        </button>

        {/* Destination */}
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">To</label>
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-indigo-400" />
            <input
              type="text"
              value={destination}
              onChange={e => setDestination(e.target.value)}
              placeholder="City or address"
              required
              className={inputClass}
            />
          </div>
        </div>

        {/* Date */}
        <div className="min-w-[150px]">
          <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">Date</label>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300 dark:text-gray-600 pointer-events-none" />
            <input
              type="date"
              value={date}
              min={today}
              onChange={e => setDate(e.target.value)}
              required
              className={inputClass}
            />
          </div>
        </div>

        {/* Time */}
        <div className="min-w-[120px]">
          <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">Time</label>
          <div className="relative">
            <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300 dark:text-gray-600 pointer-events-none" />
            <input
              type="time"
              value={time}
              onChange={e => setTime(e.target.value)}
              required
              className={inputClass}
            />
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-6 py-2.5 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-300 dark:disabled:bg-sky-900 text-white font-semibold rounded-xl transition-colors text-sm whitespace-nowrap shadow-sm shadow-sky-200 dark:shadow-none"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              Find routes
            </>
          )}
        </button>
      </div>
    </form>
  );
}
