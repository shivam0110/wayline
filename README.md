# Wayline

A compact React + Django weather-aware truck route planner. Enter two cities, departure time and cargo weight, compare real routes, inspect checkpoint forecasts, and scrub a 0–48-hour corridor weather layer. No API keys or database required.

## Run

Requires Python 3.12+ and Node 20.19+ (Node 22.12+ also supported).

```sh
make install
make dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to Django on port 8000. Default example: Chicago → Detroit. Click **Find my routes**; forecasts are live, never fixtures.

To build and serve everything from Django at http://127.0.0.1:8000:

```sh
make serve
```

`make test` runs the compact backend suite and the TypeScript/production build. No database setup or migrations are needed.

Optional environment variables: `SECRET_KEY`, `ALLOWED_HOSTS` (comma separated), `DEBUG` (`true` enables development mode), and `PORT` (defaults to 8000). `make` loads a root `.env`; Docker expects environment variables. `.env.example` contains names only. When configuring a host, set a random secret and its allowed hostname.

## What is implemented

- City search with explicit candidate selection; departure labeled in the browser's timezone.
- Requests a primary route and two alternatives. Shows the actual distinct routes returned, with a warning when fewer than three exist.
- Keyless Valhalla truck routing. If unavailable or beyond its limits, OSRM standard road routing is used with an explicit truck-restriction warning.
- Origin, 10/25/50-mile checkpoints, and destination along the road geometry, with arrival-time forecasts and clickable weather/risk details.
- Risk-colored segments, selectable route cards, arrival times, Severe/High miles, distance-weighted average risk, and exclusion reasons.
- A real coarse 2D polygon grid within approximately 25 miles of the routes. At most 120 cells; larger trips get coarser cells. Wind/rain/snow layers, units, legend, gray unavailable cells.
- 49 forecast timestamps, from the current UTC hour through +48 hours. Slider updates locally without requests. Route risks remain tied to checkpoint arrival times.
- Timeouts, bounded input sizes and forecast batches, canceled stale UI requests, cached forecasts, distinct provider errors and No Travel states.

## Rules and assumptions

These implement the assignment; they are not independently validated driving safety thresholds.

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Sustained wind, mph | <25 | 25–<35 | 35–<45 | 45–<55 | ≥55 |
| Rain, in/hr | <0.10 | 0.10–<0.25 | 0.25–<0.50 | 0.50–1.00 | >1.00 |
| Snow, in/hr | <0.5 | 0.5–<1 | 1–<2 | 2–3 | >3 |

Wind ≥55 mph blocks any load. Wind 45–<55 mph with **>30,000 lb** blocks travel. Wind 35–<45 mph with **>40,000 lb** raises risk to Severe. Exact load boundaries do not trigger the overrides. Classify full precision, then round for display. The final risk is the maximum of wind, rain, snow and load override.

A segment takes the worse risk of its two endpoints; this approximates conditions between samples. Segment miles include the last partial segment and sum to provider road mileage. Average risk is `Σ(segment miles × risk) / total miles`, with Low=0 through No Travel=4. Missing required weather is Unknown and never assumed Low.

Routes containing No Travel or Unknown segments are excluded. Eligible routes rank lexicographically by `(Severe miles, High miles, average risk, travel seconds, route ID)`. If none is eligible, the app recommends no route and retains every alternative.

Checkpoint positions use geographic distance along the full road polyline, scaled to provider mileage. ETAs use OSRM per-edge times or Valhalla maneuver times distributed within each maneuver by distance. If per-vertex times are missing, proportional distance × total duration is used. No traffic, breaks, fuel stops or HOS model. Valhalla uses its default truck dimensions/gross weight: cargo weight is deliberately **not** passed as gross vehicle weight.

Open-Meteo `wind_speed_10m` is sustained wind in mph, interpolated between adjacent hours. Rain is `rain + showers` in mm, divided by 25.4. Snowfall is cm, divided by 2.54. Rain and snow are preceding-hour accumulations, interpreted as average in/hr for the interval ending at the first timestamp ≥ETA. Forecasts outside the available timestamps remain Unknown; nothing is clamped.

Departures must be future and within six days. Seven calendar days of hourly weather are requested, so arrivals near/beyond that horizon may lack forecasts. Demo limits: 2,500 road miles per route, 600 total checkpoints, latitude within ±75°, no date-line crossings. Valhalla's public server imposes additional distance limits; the fallback is clearly labeled. The corridor projection is approximate and its displayed cell size describes sampling, not native forecast accuracy.

## Code

```text
backend/planner/
  providers.py   routing/geocoding/weather clients and in-process caches
  routing.py     polyline sampling, ETAs and bounded corridor grid
  weather.py     hourly matching and unit conversion
  risk.py        thresholds, load rules, aggregation and recommendation
  views.py       validation and three JSON endpoints
  tests/         boundaries, weights, ranking, geometry, weather time and API checks
frontend/src/
  App.tsx        request orchestration and selected route/hour
  components/    form, route cards, Leaflet map and forecast controls
```

API: `GET /api/geocode?q=...`, `POST /api/plan` (`origin`, `destination` as `[lon,lat]`, `departure` ISO with timezone, `load_lb`, `interval_miles`), `POST /api/corridor-weather` (`routes`: arrays of `[lon,lat]`), `GET /api/health`.

React/Vite and Leaflet render the UI. Plain Django JSON endpoints keep server logic small. No accounts, trip persistence, background workers, Redis or runtime AI. Forecasts use batches of 20 locations with at most three concurrent requests. In-memory caches expire after 15 minutes for weather, 10 minutes for routes and one hour for geocoding; each process has its own bounded cache.

## Deployment

The Dockerfile builds the frontend and serves the API and static files through Django, WhiteNoise and Gunicorn. `render.yaml` configures a single free-plan service. Push this repository to your GitHub account, then create a Render Blueprint using it. Other Docker-capable Python hosts also work:

```sh
docker build -t wayline .
docker run --rm -p 8000:8000 -e ALLOWED_HOSTS=localhost,127.0.0.1 wayline
```

**Hosted URL:** not deployed yet. **Loom:** not recorded yet. These are remaining submission steps, not completed deliverables. Free hosting availability and public API limits can change; free services may sleep or throttle. This is a demo, not a production navigation service.

## Providers and references

- [Valhalla](https://valhalla.openstreetmap.de/) / [FOSSGIS routing server](https://valhalla1.openstreetmap.de/): default truck routing.
- [OSRM](https://project-osrm.org/): standard road fallback; OpenStreetMap data.
- [Open-Meteo](https://open-meteo.com/en/docs): hourly forecasts and [GeoNames-backed place search](https://open-meteo.com/en/docs/geocoding-api). Public APIs are for appropriate demo/noncommercial use and have fair-use limits; batching does not eliminate per-location quota accounting.
- Map attribution: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) displayed on the map. Public tiles follow the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

Reference repositories reviewed for implementation ideas: [OzairKhanBro](https://github.com/OzairKhanBro/spotter-truck-routing) (keyless truck routes, arrival-time matching, risk strips), [Madesh frontend](https://github.com/Madesh-cse/spotter-truck-routing-frontend) / [backend](https://github.com/Madesh-cse/spotter-truck-routing-backend) (Leaflet layout and isolated risk functions), and [dohoudaniel](https://github.com/dohoudaniel/spotter-backend-django) (plain Django and small routing payloads). [Shruti-Apte](https://github.com/Shruti-Apte/truck-route-planner), [FelixBC](https://github.com/FelixBC/spotter-eld), and [TheACJ](https://github.com/TheACJ/spotter_trip_planner) address different ELD/HOS assignments. Implemented independently; no third-party application source was copied.

## 5–10 minute walkthrough

1. Enter locations, departure, cargo and checkpoint interval; plan a trip.
2. Compare returned alternatives and explain recommendation order and exclusions.
3. Select a route and click checkpoints to show ETA-matched weather and load rules.
4. Switch wind/rain/snow and move the 0–48h slider; show that route risks stay fixed.
5. Briefly show `risk.py`, `weather.py` and tests; explain interpolation, provider limits and the truck-profile assumptions.
