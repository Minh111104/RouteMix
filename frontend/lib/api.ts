import { FlexibleDatesResponse, SearchRequest, SearchResponse } from './types';

export async function searchRoutes(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch('/api/compose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? 'Failed to fetch routes');
  }

  return response.json();
}

export async function getFlexibleDates(
  origin: string,
  destination: string,
  centerDate: string,
): Promise<FlexibleDatesResponse> {
  const response = await fetch('/api/flexible-dates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ origin, destination, center_date: centerDate }),
  });
  if (!response.ok) throw new Error('Failed to fetch flexible dates');
  return response.json();
}
