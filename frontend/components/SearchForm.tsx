'use client';

import { useState } from 'react';
import { MapPin, Calendar, Clock, ArrowLeftRight, Search, Loader2, Plus, X } from 'lucide-react';
import { SearchRequest } from '@/lib/types';

interface InitialValues {
  origin: string;
  destination: string;
  date: string;
  time: string;
  waypoints: string[];
}

interface Props {
  onSearch: (req: SearchRequest) => void;
  loading: boolean;
  initialValues?: InitialValues;
}

export default function SearchForm({ onSearch, loading, initialValues }: Props) {
  const [origin, setOrigin] = useState(initialValues?.origin ?? '');
  const [destination, setDestination] = useState(initialValues?.destination ?? '');
  const [waypoints, setWaypoints] = useState<string[]>(initialValues?.waypoints ?? []);
  const [date, setDate] = useState(initialValues?.date ?? '');
  const [time, setTime] = useState(initialValues?.time ?? '09:00');

  const today = new Date().toISOString().split('T')[0];

  function handleSwap() {
    setOrigin(destination);
    setDestination(origin);
  }

  function addWaypoint() {
    if (waypoints.length < 4) setWaypoints(prev => [...prev, '']);
  }

  function removeWaypoint(idx: number) {
    setWaypoints(prev => prev.filter((_, i) => i !== idx));
  }

  function updateWaypoint(idx: number, val: string) {
    setWaypoints(prev => prev.map((w, i) => (i === idx ? val : w)));
  }

  function handleSubmit(e: { preventDefault(): void }) {
    e.preventDefault();
    const filteredWaypoints = waypoints.filter(w => w.trim());
    onSearch({
      origin,
      destination,
      waypoints: filteredWaypoints.length ? filteredWaypoints : undefined,
      departure_time: `${date}T${time}:00`,
      preference: 'balanced',
    });
  }

  const inputClass =
    'w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 placeholder-gray-300 dark:placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent text-sm';

  const hasWaypoints = waypoints.length > 0;

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-800 p-5"
    >
      {/* Stops section */}
      <div className="flex gap-3 mb-3">
        {/* Timeline dots + line */}
        <div className="flex flex-col items-center pt-8 shrink-0">
          <div className="w-2.5 h-2.5 rounded-full bg-sky-500 shrink-0" />
          <div className="w-px flex-1 bg-gray-200 dark:bg-gray-700 my-1" />
          {waypoints.map((_, i) => (
            <div key={i} className="flex flex-col items-center w-full">
              <div className="w-2 h-2 rounded-full border-2 border-sky-400 bg-white dark:bg-gray-900 shrink-0" />
              <div className="w-px flex-1 bg-gray-200 dark:bg-gray-700 my-1" />
            </div>
          ))}
          <div className="w-2.5 h-2.5 rounded-sm bg-indigo-500 shrink-0" />
        </div>

        {/* Inputs column */}
        <div className="flex-1 space-y-2">
          {/* Origin */}
          <div>
            <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">
              From
            </label>
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

          {/* Waypoints */}
          {waypoints.map((wp, i) => (
            <div key={i}>
              <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">
                Stop {i + 1}
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-300" />
                  <input
                    type="text"
                    value={wp}
                    onChange={e => updateWaypoint(i, e.target.value)}
                    placeholder="City or address"
                    className={inputClass}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeWaypoint(i)}
                  className="p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-400 hover:text-red-500 hover:border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors shrink-0"
                  title="Remove stop"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {/* Destination */}
          <div>
            <label className="block text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1.5">
              To
            </label>
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
        </div>
      </div>

      {/* Controls row */}
      <div className="flex flex-wrap gap-3 items-end">
        {/* Add stop / Swap */}
        {waypoints.length < 4 && (
          <button
            type="button"
            onClick={addWaypoint}
            className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-dashed border-sky-300 dark:border-sky-700 text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-900/20 text-xs font-semibold transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add stop
          </button>
        )}

        {!hasWaypoints && (
          <button
            type="button"
            onClick={handleSwap}
            className="p-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 hover:text-sky-600 hover:border-sky-300 hover:bg-sky-50 dark:hover:bg-sky-900/20 transition-colors"
            title="Swap origin and destination"
          >
            <ArrowLeftRight className="w-4 h-4" />
          </button>
        )}

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
