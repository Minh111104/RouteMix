'use client';

import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import SearchForm from '@/components/SearchForm';
import RouteCard from '@/components/RouteCard';
import FilterBar from '@/components/FilterBar';
import { searchRoutes } from '@/lib/api';
import { ComposedRoute, SearchRequest, SortFilter } from '@/lib/types';

// Leaflet must only run on the client — load MapView without SSR
const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

function sortRoutes(routes: ComposedRoute[], filter: SortFilter): ComposedRoute[] {
  const copy = [...routes];
  if (filter === 'cheap') return copy.sort((a, b) => a.total_cost_usd - b.total_cost_usd);
  if (filter === 'fast') return copy.sort((a, b) => a.total_duration_minutes - b.total_duration_minutes);
  if (filter === 'transfers') return copy.sort((a, b) => a.transfers - b.transfers);
  return copy; // 'all' — keep backend order (balanced score)
}

export default function Home() {
  const [routes, setRoutes] = useState<ComposedRoute[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [filter, setFilter] = useState<SortFilter>('all');
  const [activeRouteType, setActiveRouteType] = useState<string | null>(null);

  async function handleSearch(req: SearchRequest) {
    setLoading(true);
    setError(null);
    setRoutes([]);
    setFilter('all');
    setActiveRouteType(null);
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

  const displayedRoutes = useMemo(() => sortRoutes(routes, filter), [routes, filter]);

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">RouteMix</h1>
        <p className="text-gray-500 mt-1">Compare every way to get there — drive, fly, transit, or mix.</p>
      </div>

      {/* Search form — always full width */}
      <SearchForm onSearch={handleSearch} loading={loading} />

      {/* Error */}
      {error && (
        <div className="mt-5 p-4 bg-red-50 border border-red-100 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
          <div className="lg:col-span-2 space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-2xl border border-gray-100 h-36 animate-pulse" />
            ))}
          </div>
          <div className="lg:col-span-3 h-[500px] bg-gray-100 rounded-2xl animate-pulse" />
        </div>
      )}

      {/* Results */}
      {!loading && searched && (
        <>
          {routes.length === 0 && !error ? (
            <p className="mt-8 text-center text-gray-400 text-sm py-12">
              No routes found. Try different locations or a later date.
            </p>
          ) : (
            <div className="mt-6 grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
              {/* Left column: filter bar + route cards */}
              <div className="lg:col-span-2 space-y-3">
                <FilterBar value={filter} onChange={setFilter} count={routes.length} />
                {displayedRoutes.map((route, i) => (
                  <RouteCard
                    key={route.route_type}
                    route={route}
                    rank={i}
                    isActive={activeRouteType === route.route_type}
                    onMouseEnter={() => setActiveRouteType(route.route_type)}
                    onMouseLeave={() => setActiveRouteType(null)}
                  />
                ))}
              </div>

              {/* Right column: sticky interactive map */}
              <div className="lg:col-span-3 sticky top-6 h-[520px] lg:h-[calc(100vh-6rem)]">
                <MapView
                  routes={routes}
                  activeRouteType={activeRouteType}
                  onRouteClick={type =>
                    setActiveRouteType(prev => (prev === type ? null : type))
                  }
                />
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
