# RouteMix

A multimodal travel planner that compares every realistic way to get from A to B — driving, public transit, flying, and hybrid combinations like drive-to-airport + fly + rideshare. Routes are scored and ranked so you can instantly find the cheapest, fastest, or best-value option.

## What makes it different

Most apps show you one mode at a time. RouteMix builds **hybrid itineraries** automatically:

- Drive to Detroit (DTW) → Fly to San Jose (SJC) → Transit to destination
- Drive only across the country
- Public transit end-to-end (where available)

Each route is scored with a weighted formula across cost, time, and transfers — and you can re-sort results client-side without a new search.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), uvicorn |
| Routing | Google Routes API (driving + transit) |
| Geocoding | Google Geocoding API |
| Flights | Serpapi — Google Flights engine |
| Airport lookup | `airportsdata` (local, no API call) |
| Map | Leaflet + OpenStreetMap (no key needed) |

## Project structure

```
RouteMix/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + CORS
│   │   ├── config.py                # loads .env keys
│   │   ├── models/route.py          # Pydantic models
│   │   ├── routers/compose.py       # POST /api/compose
│   │   └── services/
│   │       ├── google_routes.py     # driving, transit, geocoding
│   │       ├── serpapi.py           # flight search via Serpapi
│   │       ├── airports.py          # nearest commercial airport finder
│   │       └── composer.py          # route composition + scoring engine
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   └── page.tsx                 # main UI
    ├── components/
    │   ├── SearchForm.tsx           # origin / destination / date inputs
    │   ├── RouteCard.tsx            # renders one route with segment breakdown
    │   ├── FilterBar.tsx            # client-side sort controls
    │   └── MapView.tsx              # interactive Leaflet map
    ├── lib/
    │   ├── types.ts
    │   └── api.ts
    └── .env.local.example
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 20+
- A [Google Cloud](https://console.cloud.google.com) project with these APIs enabled:
  - **Routes API**
  - **Geocoding API**
- A [Serpapi](https://serpapi.com) account (free tier: 100 searches/month)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/RouteMix.git
cd RouteMix
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and fill in your keys
```

`.env` should look like:

```env
GOOGLE_ROUTES_API_KEY=AIza...
SERPAPI_KEY=your_serpapi_key_here
```

Start the backend:

```bash
uvicorn app.main:app --reload
# Runs on http://localhost:8000
```

### 3. Frontend

```bash
cd frontend

npm install

cp .env.local.example .env.local
# Default value (BACKEND_URL=http://localhost:8000) is fine for local dev

npm run dev
# Runs on http://localhost:3000
```

## API keys

### Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Library
2. Enable **Routes API** and **Geocoding API**
3. Go to Credentials → Create API Key
4. Restrict the key to those two APIs (recommended)

The `$200/month` free credit covers heavy development usage.

### Serpapi

1. Sign up at [serpapi.com](https://serpapi.com)
2. Copy your API key from the dashboard
3. Free tier: **100 searches/month** — enough for development and demos

> The app works with just the Google key. If `SERPAPI_KEY` is empty, flight routes are silently skipped and only driving + transit are returned.

## How it works

### Route composition engine

`composer.py` builds all route types in parallel:

1. **Drive only** — Google Routes API, cost estimated from distance × gas price
2. **Transit only** — Google Routes API transit mode (available for connected cities)
3. **Fly routes** — for each pair of nearby commercial airports:
   - Geocode origin/destination
   - Find nearest airports using local `airportsdata` database (no API call)
   - Filter out GA airports by name heuristic
   - Search Serpapi for flights between airport pairs
   - Build: drive-to-airport + flight + transit/rideshare-from-airport

### Scoring formula

Each route is scored:

```
score = cost_weight × (cost / max_cost)
      + time_weight × (time / max_time)
      + transfer_weight × (transfers / 3)
```

Weights by priority preset:

| Preset | Cost | Time | Transfers |
|--------|------|------|-----------|
| Save money | 0.7 | 0.2 | 0.1 |
| Save time | 0.1 | 0.8 | 0.1 |
| Balanced | 0.4 | 0.4 | 0.2 |

### Map visualization

Routes are drawn as color-coded polylines on an OpenStreetMap base layer:

| Mode | Color |
|------|-------|
| Drive | Blue |
| Transit | Green |
| Flight | Purple (dashed) |
| Rideshare | Orange |

Hover a route card to highlight it on the map. Click a polyline to select the corresponding card.

## Development notes

- The backend hot-reloads on file changes (`--reload` flag)
- Next.js proxies `/api/*` to `localhost:8000` via `next.config.ts` rewrites
- Serpapi uses sandbox/live data depending on your account tier
- Transit fare data from Google is often unavailable for long-distance routes — the app shows "Fare unavailable" in that case

## License

This project is made for educational purpose.
