# Deployment

Prepared configuration is included; an actual hosted deployment has not been performed. Import the same Git repository as **two Vercel projects** with root directories `backend` and `frontend`. Enable Fluid compute on the API project. This follows the official [Django](https://vercel.com/docs/frameworks/full-stack/django), [Python](https://vercel.com/docs/functions/runtimes/python), [monorepo](https://vercel.com/docs/monorepos) and [function limits](https://vercel.com/docs/functions/limitations) documentation checked on 2026-10-02.

## API project (`backend`)

Django is detected through `manage.py`; `pyproject.toml` names `config.wsgi:application`. `vercel.json` configures that entrypoint for 240 seconds, above the 180-second planning deadline and below the documented 300-second Hobby Fluid-compute maximum. Production dependency constraints are in `requirements.txt`; the complete local/CI environment is pinned in `requirements.lock.txt`. There is no persistent database.

Set these server-only environment variables in the Vercel dashboard:

| Variable | Value |
| --- | --- |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | Stable random secret, at least 50 characters; use the same value across instances/deployments |
| `DJANGO_ALLOWED_HOSTS` | Exact API production/preview hostnames, comma separated, without schemes |
| `FRONTEND_ORIGINS` | Exact permitted frontend origins, including `https://`, comma separated |
| `ORS_API_KEY` | Private openrouteservice key |
| `PROVIDER_MODE` | `live` |
| `STOP_PROVIDER` | `dot` (default): DOT truck parking plus ORS fuel POIs and original OSM access tags |
| `ORS_MIN_INTERVAL_S` | Start with `2`; adjust from the account's current quotas |
| `OVERPASS_MIN_INTERVAL_S` | Start with `2`; adjust to the chosen endpoint's service policy |

Use `backend/.env.production.example` as the required-variable reference. On a non-Vercel host also set `HAUL_HOURS_PRODUCTION=true`. Production startup rejects a missing routing key, blank/wildcard hosts, non-HTTPS origins and non-HTTPS provider endpoints. HTTPS redirect, secure cookie settings, frame denial and a one-year HSTS policy apply in production. Vercel's trusted forwarded HTTPS header prevents redirect loops; other proxy hosts must explicitly set `DJANGO_TRUST_PROXY=true` only behind a proxy that overwrites the header. HSTS subdomain inclusion and preload are deliberately disabled because unrelated subdomains have not been audited.

Generate a signing secret locally with `backend/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(64))'` and store it privately. Do not commit it. Hosting startup rejects fixture mode, debug mode and the default/short secret. Rotating the secret invalidates existing PDF tokens; tokens also expire in 24 hours. Add optional `ORS_BASE_URL` / `OVERPASS_URL` only when deliberately selecting compatible providers.

Provider quotas are account dependent. Before publishing, record daily and per-minute directions/matrix/geocoding/**POI** quotas from the key's dashboard, choose request intervals accordingly, and run the live smoke command. The default two-second spacing is process local and does not enforce a daily or global serverless quota. Caches can disappear between requests. DOT and OSM services are external dependencies. The API returns explicit retryable 429/503/504 responses rather than fabricating a result.

The default stop adapter obtains long-rest evidence from the [USDOT/BTS Truck Stop Parking inventory](https://data-usdot.opendata.arcgis.com/datasets/usdot::truck-stop-parking/about), requiring a positive recorded truck-space count. It searches within 20 km of the bounded route samples; every accepted approach/exit still requires actual truck directions and the duty/fuel audit. This inventory was compiled in April 2019 and is **not a live parking-availability feed**. The UI includes that limitation. Fuel candidates come from the existing key's ORS POI service; original OSM records confirm access restrictions. Provider credentials are sent only to the routing gateway.

`STOP_PROVIDER=overpass` retains the configurable Overpass adapter. Queries use separate cached geographic windows and can fail over once per configured `OVERPASS_FALLBACK_URLS` endpoint (at most two). Authentication errors, rate limits and exhausted budgets do not rotate endpoints. For commercial/high-traffic use choose a dedicated or paid endpoint; the [public Overpass instance policy](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances) does not promise production availability. Backups are opt-in so private providers never silently fall back to public servers.

## Frontend project (`frontend`)

Use the Vite framework preset and Node 24. Enable **Include source files outside of the Root Directory** so the root npm workspace/lock and shared contracts are included. The supplied `vercel.json` installs/builds from the monorepo root and publishes `frontend/dist` (output directory `dist` relative to project root). Set `VITE_API_BASE_URL=https://YOUR-API-DOMAIN` and redeploy; this variable is compiled into the client. Set the matching origin in backend CORS before testing. Provider and signing keys never belong in the frontend environment.

The hosted frontend build now fails immediately when its API URL is missing or is not an HTTPS URL. `frontend/.env.production.example` lists its only required production variable.

## Live acceptance command

After starting the live API, run:

```sh
HAUL_HOURS_API_URL=http://127.0.0.1:8010 npm run test:live
```

Replace the URL with the deployed HTTPS API to repeat these checks after deployment. The command refuses fixture mode and verifies real short, overnight, fuel and 34-hour restart trips, full daily totals, the 1,000-mile fuel bound, and single/all-day PDF bytes and sizes. Run one scenario with `npm run test:live -- overnight` (or `short`, `fuel`, `restart`) to limit quota use. A failed scenario is reported as a failure, not replaced by demo data.

## Hosted acceptance

Local live acceptance passed on 2026-10-05 using the real configured ORS key and the default DOT/ORS/OSM stop adapter:

| Scenario | Route | Observed result |
| --- | --- | --- |
| Short | Pittsburgh → Harrisburg → Philadelphia | 1 daily log |
| Overnight | Pittsburgh → Harrisonburg, VA → Philadelphia | 2 daily logs, 1 daily rest |
| Fuel | Los Angeles → Phoenix → Dallas | 4 daily logs, 1 fuel stop, 4 daily rests |
| Cycle exhausted | Short route with 70 hours already worked | 2 daily logs, 34-hour cycle restart |

All four passed timeline/daily-total checks, the fuel-distance bound, and single-day/all-day PDF checks. These results describe the tested routes and provider responses, not guaranteed coverage or future provider availability. Automated verification passed 124 backend tests and 26 frontend tests, strict TypeScript, lint, contract consistency and the production build. Django's production deploy check had no errors; its two HSTS warnings reflect the deliberate subdomain/preload choices above.

1. Run local CI commands and push the reviewed implementation using the repository owner's account.
2. Deploy the API and verify `/api/v1/health`; it must return provider-mode header `live`.
3. Deploy the frontend with the API origin. Verify geocoding and network CORS in a fresh browser.
4. Run short, fuel, multi-day and cycle-exhaustion routes using actual addresses; check accepted stop detours and all hours/fuel bounds. Live map conditions may legitimately block a route; record that distinctly from correctness tests.
5. Download PDF for one day and all days; compare dates/totals to the displayed sheets. Keep JSON/PDF payloads below 4 MB (the platform limit is 4.5 MB). Confirm visible OSM attribution and absent secrets in the generated client bundle.
6. Verify GitHub, hosted URL and Loom access in a reviewer/private browsing context; then replace the pending delivery entries in README.

Account-wide quotas, deployed function bundle size/cold start, hosted smoke checks, reviewer visibility and Loom recording remain external checks. The prepared files and local live smoke checks do not constitute a successful hosted deployment.
