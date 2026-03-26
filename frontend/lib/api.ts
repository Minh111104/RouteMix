import { SearchRequest, SearchResponse } from './types';

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
