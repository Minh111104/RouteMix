'use client';

import { useState, FormEvent } from 'react';
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

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSearch({ origin, destination, departure_time: `${date}T${time}:00`, preference: 'balanced' });
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 flex flex-wrap gap-3 items-end">
      <div className="flex-1 min-w-[140px]">
        <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
        <input
          type="text"
          value={origin}
          onChange={e => setOrigin(e.target.value)}
          placeholder="e.g. Bowling Green, OH"
          required
          className="w-full px-3 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
        />
      </div>
      <div className="flex-1 min-w-[140px]">
        <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
        <input
          type="text"
          value={destination}
          onChange={e => setDestination(e.target.value)}
          placeholder="e.g. Toronto, ON"
          required
          className="w-full px-3 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
        />
      </div>
      <div className="min-w-[130px]">
        <label className="block text-xs font-medium text-gray-500 mb-1">Date</label>
        <input
          type="date"
          value={date}
          min={today}
          onChange={e => setDate(e.target.value)}
          required
          className="w-full px-3 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
        />
      </div>
      <div className="min-w-[110px]">
        <label className="block text-xs font-medium text-gray-500 mb-1">Time</label>
        <input
          type="time"
          value={time}
          onChange={e => setTime(e.target.value)}
          required
          className="w-full px-3 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="px-6 py-2.5 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-300 text-white font-semibold rounded-lg transition-colors text-sm whitespace-nowrap"
      >
        {loading ? 'Searching...' : 'Find routes'}
      </button>
    </form>
  );
}
