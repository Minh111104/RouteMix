# RouteMix

A multimodal travel planner that compares every realistic way to get from A to B — driving, public transit, intercity train, intercity bus, flying, and hybrid combinations like drive-to-airport + fly + rideshare. Routes are scored and ranked so you can instantly find the cheapest, fastest, or best-value option.

## What makes it different

Most apps show you one mode at a time. RouteMix builds **all viable itineraries** automatically and ranks them side-by-side:

- Drive to DTW → Fly DTW→LGA → Rideshare to destination
- Drive only across the country
- Intercity train (estimate based on distance)
- Intercity bus (estimate · e.g. Greyhound / FlixBus)
- Public transit end-to-end (where Google has schedule data)

Each route is scored with a weighted formula across cost, time, and transfers — and you can re-sort results client-side without a new search.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), uvicorn |
| Routing | Google Routes API (driving + transit polylines) |
| Geocoding | Google Geocoding API |
| Flights | Serpapi — Google Flights engine |
| Airport lookup | `airportsdata` (local IATA database, no API call) |
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
│   │       ├── google_routes.py     # driving, transit, geocoding + polylines
│   │       ├── serpapi.py           # flight search via Serpapi
│   │       ├── airports.py          # nearest commercial airport finder
│   │       └── composer.py          # route composition + scoring engine
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── layout.tsx               # font, dark mode provider
    │   └── page.tsx                 # hero, search, results layout
    ├── components/
    │   ├── SearchForm.tsx           # origin / destination / date / time inputs
    │   ├── RouteCard.tsx            # timeline-style segment breakdown per route
    │   ├── FilterBar.tsx            # client-side sort controls
    │   ├── MapView.tsx              # interactive Leaflet map with real polylines
    │   ├── ThemeProvider.tsx        # applies saved dark/light preference on load
    │   └── ThemeToggle.tsx          # sun/moon button in the hero header
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

> The app works with just the Google key. If `SERPAPI_KEY` is empty, flight routes are silently skipped and only ground routes are returned.

## How it works

### Route composition engine

`composer.py` builds all route types in parallel:

1. **Drive only** — Google Routes API; cost estimated from distance × gas price; real road polyline on map
2. **Transit only** — Google Routes API transit mode; real route polyline returned where Google has schedule data
3. **Train** — distance-based estimate (~80 km/h avg, ~$0.13/km); shown for routes ≥ 150 km
4. **Bus** — distance-based estimate (~70 km/h avg, ~$0.07/km); shown for routes ≥ 100 km
5. **Fly routes** — for each pair of nearby commercial airports:
   - Find nearest airports using local `airportsdata` database (no API call)
   - Filter out GA airports by name heuristic; positive override for "international / metro" airports
   - Search Serpapi for flights between airport pairs
   - Build: drive-to-airport + flight + transit/rideshare-from-airport
   - Drive legs use real road polylines; flight leg renders as a dashed straight line

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

Routes are drawn as color-coded polylines on an OpenStreetMap base layer. Drive and transit segments use the real encoded polyline from Google Routes API; flight segments use a dashed straight line; train and bus use a straight line to indicate they are estimates.

| Mode | Color | Line style |
|------|-------|------------|
| Drive | Blue | Road-following polyline |
| Transit | Green | Road/rail-following polyline |
| Train | Teal | Straight line (estimate) |
| Bus | Amber | Straight line (estimate) |
| Flight | Purple | Dashed straight line |
| Rideshare | Orange | Road-following polyline |

Hover a route card to highlight it on the map. Click a polyline to select the corresponding card.

### Dark mode

The UI supports light and dark mode. The preference is saved in `localStorage` and automatically applied on page load. The toggle is in the top-right corner of the hero header; the initial value respects the OS `prefers-color-scheme` setting.

## Development notes

- The backend hot-reloads on file changes (`--reload` flag)
- Next.js proxies `/api/*` to `localhost:8000` via `next.config.ts` rewrites
- Serpapi uses sandbox/live data depending on your account tier
- Transit fare data from Google is often unavailable for long-distance routes — the app shows "Fare unavailable" in that case
- Google Transit 400 errors on cross-country routes are expected (no connected network) and logged at DEBUG level only

## License

This project is made for educational purposes.
