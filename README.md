# Haul Hours

A Django + React trip planner for a single property-carrying driver. Plan a truck route with fuel, breaks, daily rests and cycle restarts; review synchronized maps, itineraries and projected daily duty sheets; download signed-snapshot PDFs.

The frontend and repository tooling use strict TypeScript. The npm workspace contains the Vite/React app, customized shadcn/ui controls and the supplied Kraken-inspired tokens. Django owns every duty calculation, accepted road detour, daily graph and export.

## Run locally

Use Node 24 and Python 3.12–3.14 (verified locally with 3.14). From the repository root:

```sh
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock.txt
npm ci
npx playwright install chromium
cp backend/.env.example backend/.env
npm run dev:demo
```

Open the URL Vite prints (normally `http://127.0.0.1:5173`). The API runs on port 8000. No database or migrations are needed. To avoid occupied ports:

```sh
HAUL_HOURS_API_PORT=8010 HAUL_HOURS_WEB_PORT=5180 npm run dev:demo
```

**Demo mode displays a Test data banner.** It uses a small directed fixture network with illustrative geometry and timings, while running the actual Django scheduler and PDF generation. It never substitutes fixtures for failed live routing. Search Pittsburgh → Harrisburg → Philadelphia for a short trip; choose San Diego for multiple days, Los Angeles for fuel, cycle usage 70 for a restart, Boston for blocked stops, or Miami for a simulated provider outage. Set optional departure to `2026-10-02T08:00` for repeatable examples. Fixture mode is refused outside debug mode and on Vercel.

For actual roads, set `ORS_API_KEY` in **backend/.env** and run `npm run dev`. Provider mode defaults to `live`. Never place the provider key in a `VITE_` variable. The development proxy connects the frontend to Django; hosted builds use `frontend/.env.example` → `VITE_API_BASE_URL`.

## Verify

```sh
npm run lint
npm run check:api
npm run contracts:check
npm test
npm run build
npm run test:e2e
```

`npm test` runs backend and frontend tests. Playwright starts separate servers on 8017/5187 with explicit fixtures, covering four representative trips, blocked/outage responses, map/log synchronization, PDF totals, edits during planning, mobile widths and print styling. CI repeats these commands. `npm run contracts:generate` regenerates JSON Schema and TypeScript from Django serializers; `contracts:check` rejects drift.

## Scheduling assumptions

- One property-carrying driver, 70 hours / 8 days, fully rested initially; entered cycle hours remain used until a 34-hour restart. Prior-day recap data is unavailable, so the planner uses restarts instead of invented recaps.
- Maximum 11 hours driving in a 14-hour window; a 30-minute non-driving interruption before driving beyond 8 accumulated hours; 10 consecutive off-duty hours reset the day. Midnight does not reset these limits.
- Pickup and drop-off each take one hour on duty. Fuel takes 30 minutes on duty and qualifies as a driving interruption. The initial fuel-distance counter is zero; accepted driving distance cannot exceed 1,000 miles between fuel events.
- A required initial restart may happen at the departure site, assumed to permit waiting. Later long rests require mapped truck-parking evidence. Fuel and off-duty rest are separate events.
- Optional departure defaults to the current instant, normalized to whole seconds for the integer-second duty model. Every daily sheet uses one selected home-terminal IANA timezone. Spring/fall DST sheets have 23/25 elapsed hours, explicit UTC offsets, and conserved totals/miles. Outside-trip portions are labeled assumed off duty; they do not extend the trip ETA.
- No adverse-condition, short-haul, split-sleeper, appointment-window or team-driver adjustments. These are projected schedules; signatures remain blank.

## Live providers and bounds

openrouteservice supplies US address search, `driving-hgv` directions and candidate matrices. Overpass supplies real OpenStreetMap fuel/services/rest-area/truck-parking POIs. Actual routes to and from each chosen stop must pass duty and fuel checks; matrix estimates alone never prove feasibility. Mapped amenities do not guarantee opening hours, parking availability or vehicle suitability.

Search is bounded: 180-second deadline, 160 external calls, 64 stops, at most 100 POIs/window, six 2 km search circles, five matrix candidates, three candidate attempts and three backtracks. Locations are limited to supported US regions (continental states, Alaska and Hawaii), with a 6,000 km maximum per base leg; ferries and border crossings are avoided. A sparse map or bounded search may report no feasible sequence even if one exists elsewhere. A blocked response includes only the verified safe prefix, without a complete ETA/export.

Uncached requests are spaced by `ORS_MIN_INTERVAL_S` and `OVERPASS_MIN_INTERVAL_S` (default two seconds per provider/process). Configure these using the actual account quotas. Process caches are expendable, bounded and do not coordinate quotas across serverless instances. Upstream 429, outages, malformed responses and deadlines are explicit; transient failures retry once within the deadline. Account-specific quota verification remains pending the routing key.

JSON and PDF sizes are capped at 4 MB. Export tokens expire after 24 hours and verify signatures before bounded decompression. A stable deployment signing secret lets the same result export across instances without rerouting.

## Project and delivery

- `backend/planner/duty`: state transitions and independent timeline audit.
- `backend/planner/scheduling`: bounded stop search and verified event timeline.
- `backend/planner/routing`: live adapters, pacing/cache and explicit fixtures.
- `backend/planner/logs`: timezone-aware sheets, backend graph geometry and PDFs.
- `frontend/src/features/trip`: typed input/results/export UI.
- [Implementation plan](docs/superpowers/plans/2026-10-02-haul-hours-implementation.md), [design system](docs/superpowers/specs/2026-10-02-haul-hours-design-system.md).
- [Deployment instructions](docs/deployment.md), [acceptance matrix](docs/acceptance.md), [four-minute walkthrough script](docs/walkthrough.md).
- Git repository: [jsmrk/haul-hours](https://github.com/jsmrk/haul-hours). Local implementation has not been pushed or its reviewer access verified.
- Hosted frontend/API and recorded Loom: pending provider key, publishing account access and recording. No live-provider or hosted success is claimed by fixture tests.

Rules reference: [FMCSA hours-of-service summary](https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations) and [ELD timezone/DST guidance](https://www.fmcsa.dot.gov/hours-service/elds/how-should-time-zone-offset-utc-handle-daylight-savings-time-1). Providers: [openrouteservice](https://openrouteservice.org/services/), [restrictions](https://openrouteservice.org/restrictions/), [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API). Road/tile data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright); visible Leaflet map attribution and [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) apply. No offline tile prefetch is implemented. Kraken font binaries are not bundled; the supplied fallback stacks are used until licensed files are provided.
