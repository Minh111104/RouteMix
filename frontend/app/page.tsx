'use client';

import { useState, useMemo, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Link, Check } from 'lucide-react';
import SearchForm from '@/components/SearchForm';
import RouteCard from '@/components/RouteCard';
import FilterBar from '@/components/FilterBar';
import ThemeToggle from '@/components/ThemeToggle';
import { searchRoutes } from '@/lib/api';
import { ComposedRoute, Preference, SearchRequest, SortFilter } from '@/lib/types';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

function sortRoutes(routes: ComposedRoute[], filter: SortFilter): ComposedRoute[] {
  const copy = [...routes];
  if (filter === 'cheap') return copy.sort((a, b) => a.total_cost_usd - b.total_cost_usd);
  if (filter === 'fast') return copy.sort((a, b) => a.total_duration_minutes - b.total_duration_minutes);
  if (filter === 'transfers') return copy.sort((a, b) => a.transfers - b.transfers);
  return copy;
}

function formatCost(usd: number) {
  if (usd === 0) return '—';
  return `$${Math.round(usd)}`;
}

function formatDuration(minutes: number) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [routes, setRoutes] = useState<ComposedRoute[]>([]);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [filter, setFilter] = useState<SortFilter>('all');
  const [activeRouteType, setActiveRouteType] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const autoSearched = useRef(false);

  // Derive initial form values from URL params
  const initialValues = useMemo(() => {
    const from = searchParams.get('from');
    const to = searchParams.get('to');
    const date = searchParams.get('date');
    const time = searchParams.get('time');
    if (!from || !to || !date) return undefined;
    return { origin: from, destination: to, date, time: time ?? '09:00' };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSearch(req: SearchRequest) {
    // Sync params into URL without triggering navigation
    const params = new URLSearchParams({
      from: req.origin,
      to: req.destination,
      date: req.departure_time.slice(0, 10),
      time: req.departure_time.slice(11, 16),
      pref: req.preference,
    });
    router.replace(`?${params.toString()}`, { scroll: false });

    setLoading(true);
    setError(null);
    setRoutes([]);
    setRecommendation(null);
    setFilter('all');
    setActiveRouteType(null);
    try {
      const data = await searchRoutes(req);
      setRoutes(data.routes);
      setRecommendation(data.recommendation ?? null);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  // Auto-fire search when URL params are present on first load
  useEffect(() => {
    if (autoSearched.current || !initialValues) return;
    autoSearched.current = true;
    const pref = (searchParams.get('pref') ?? 'balanced') as Preference;
    handleSearch({
      origin: initialValues.origin,
      destination: initialValues.destination,
      departure_time: `${initialValues.date}T${initialValues.time}:00`,
      preference: pref,
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const displayedRoutes = useMemo(() => sortRoutes(routes, filter), [routes, filter]);

  const cheapest = routes.length ? Math.min(...routes.map(r => r.total_cost_usd).filter(c => c > 0)) : null;
  const fastest = routes.length ? Math.min(...routes.map(r => r.total_duration_minutes)) : null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Hero header */}
      <div className="bg-gradient-to-br from-sky-600 via-sky-700 to-indigo-800 relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />
        <div className="relative max-w-7xl mx-auto px-4 pt-10 pb-16">
          <div className="flex items-start justify-between">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 text-sky-200 text-sm font-medium tracking-wide uppercase">
                <span className="w-4 h-px bg-sky-400 inline-block" />
                Multimodal Travel Planner
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight mb-2">
                Route<span className="text-sky-300">Mix</span>
              </h1>
              <p className="text-sky-100 text-lg max-w-xl">
                Compare every way to get there — drive, fly, transit, or mix them all.
              </p>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </div>

      {/* Search card overlapping hero */}
      <div className="max-w-7xl mx-auto px-4">
        <div className="-mt-8 relative z-10">
          <SearchForm onSearch={handleSearch} loading={loading} initialValues={initialValues} />
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 pb-16">
        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-xl text-red-700 dark:text-red-400 text-sm flex items-start gap-3">
            <span className="mt-0.5">⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="mt-8 grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
            <div className="lg:col-span-2 space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden animate-pulse">
                  <div className="h-16 bg-gray-100 dark:bg-gray-700" />
                  <div className="p-4 space-y-2">
                    <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-3/4" />
                    <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
            <div className="lg:col-span-3 h-[520px] bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />
          </div>
        )}

        {/* Results */}
        {!loading && searched && (
          <>
            {routes.length === 0 && !error ? (
              <div className="mt-12 text-center py-16">
                <p className="text-4xl mb-3">🗺️</p>
                <p className="text-gray-500 dark:text-gray-400 font-medium">No routes found</p>
                <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">Try different locations or a later departure date.</p>
              </div>
            ) : (
              <>
                {/* AI recommendation */}
                {recommendation && (
                  <div className="mt-8 flex gap-3 p-4 rounded-2xl bg-gradient-to-r from-indigo-50 to-sky-50 dark:from-indigo-950/40 dark:to-sky-950/40 border border-indigo-100 dark:border-indigo-900">
                    <span className="text-lg shrink-0">✦</span>
                    <p className="text-sm text-indigo-900 dark:text-indigo-200 leading-relaxed">{recommendation}</p>
                  </div>
                )}

                {/* Stats bar */}
                <div className={`${recommendation ? 'mt-4' : 'mt-8'} mb-4 flex flex-wrap gap-4 items-center justify-between`}>
                  <div className="flex items-center gap-6">
                    <div>
                      <p className="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide font-medium">Routes found</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">{routes.length}</p>
                    </div>
                    {cheapest !== null && (
                      <>
                        <div className="w-px h-8 bg-gray-200 dark:bg-gray-700" />
                        <div>
                          <p className="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide font-medium">Cheapest</p>
                          <p className="text-2xl font-bold text-green-600">{formatCost(cheapest)}</p>
                        </div>
                      </>
                    )}
                    {fastest !== null && (
                      <>
                        <div className="w-px h-8 bg-gray-200 dark:bg-gray-700" />
                        <div>
                          <p className="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide font-medium">Fastest</p>
                          <p className="text-2xl font-bold text-sky-600">{formatDuration(fastest)}</p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Share button */}
                  <button
                    onClick={handleShare}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-600 dark:text-gray-400 hover:border-sky-400 hover:text-sky-600 dark:hover:text-sky-400 transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 text-green-500" />
                        <span className="text-green-600 dark:text-green-400">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Link className="w-4 h-4" />
                        Share
                      </>
                    )}
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
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
              </>
            )}
          </>
        )}

        {/* Empty state before search */}
        {!loading && !searched && (
          <div className="mt-16 text-center py-8">
            <p className="text-5xl mb-4">✈️</p>
            <p className="font-medium text-gray-500 dark:text-gray-400">Enter your origin and destination above to compare routes</p>
            <p className="text-sm mt-1 text-gray-400 dark:text-gray-500">Driving · Transit · Flights · Hybrid combinations</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
