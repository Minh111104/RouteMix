'use client';

import { useState } from 'react';
import SearchForm from '@/components/SearchForm';
import RouteCard from '@/components/RouteCard';
import { searchRoutes } from '@/lib/api';
import { ComposedRoute, SearchRequest } from '@/lib/types';

export default function Home() {
  const [routes, setRoutes] = useState<ComposedRoute[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch(req: SearchRequest) {
    setLoading(true);
    setError(null);
    setRoutes([]);
    try {
      const data = await searchRoutes(req);
      setRoutes(data.routes);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      {/* Heading */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">RouteMix</h1>
        <p className="text-gray-500 mt-1">
          Compare every way to get there — drive, fly, transit, or mix.
        </p>
      </div>

      <SearchForm onSearch={handleSearch} loading={loading} />

      {/* Error */}
      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-100 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="mt-8 space-y-4">
          {[1, 2, 3].map(i => (
            <div
              key={i}
              className="bg-white rounded-2xl border border-gray-100 h-36 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && searched && routes.length === 0 && !error && (
        <div className="mt-8 text-center py-12 text-gray-400 text-sm">
          No routes found for this journey. Try different locations.
        </div>
      )}

      {/* Results */}
      {!loading && routes.length > 0 && (
        <div className="mt-8 space-y-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">
            {routes.length} route{routes.length > 1 ? 's' : ''} found · sorted by your priority
          </p>
          {routes.map((route, i) => (
            <RouteCard key={`${route.route_type}-${i}`} route={route} rank={i} />
          ))}
        </div>
      )}
    </main>
  );
}
