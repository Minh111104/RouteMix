'use client';

import { useState, FormEvent } from 'react';
import { Preference, SearchRequest } from '@/lib/types';

interface Props {
  onSearch: (req: SearchRequest) => void;
  loading: boolean;
}

const PREFERENCES: { value: Preference; label: string }[] = [
  { value: 'cheap', label: 'Save money' },
  { value: 'fast', label: 'Save time' },
  { value: 'balanced', label: 'Balanced' },
];

export default function SearchForm({ onSearch, loading }: Props) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('09:00');
  const [preference, setPreference] = useState<Preference>('balanced');

  const today = new Date().toISOString().split('T')[0];

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSearch({ origin, destination, departure_time: `${date}T${time}:00`, preference });
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">From</label>
          <input
            type="text"
            value={origin}
            onChange={e => setOrigin(e.target.value)}
            placeholder="e.g. Bowling Green, OH"
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
          <input
            type="text"
            value={destination}
            onChange={e => setDestination(e.target.value)}
            placeholder="e.g. Toronto, ON"
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
          <input
            type="date"
            value={date}
            min={today}
            onChange={e => setDate(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Departure time</label>
          <input
            type="time"
            value={time}
            onChange={e => setTime(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
        <div className="grid grid-cols-3 gap-2">
          {PREFERENCES.map(p => (
            <button
              key={p.value}
              type="button"
              onClick={() => setPreference(p.value)}
              className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                preference === p.value
                  ? 'border-sky-500 bg-sky-50 text-sky-700'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-300 text-white font-semibold rounded-lg transition-colors text-sm"
      >
        {loading ? 'Searching routes...' : 'Find routes'}
      </button>
    </form>
  );
}
