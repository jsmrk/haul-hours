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
| `ORS_MIN_INTERVAL_S` | Start with `2`; adjust from the account's current quotas |
| `OVERPASS_MIN_INTERVAL_S` | Start with `2`; adjust to the chosen endpoint's service policy |

Generate a signing secret locally with `backend/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(64))'` and store it privately. Do not commit it. Hosting startup rejects fixture mode, debug mode and the default/short secret. Rotating the secret invalidates existing PDF tokens; tokens also expire in 24 hours. Add optional `ORS_BASE_URL` / `OVERPASS_URL` only when deliberately selecting compatible providers.

Provider quotas are account dependent. Before publishing, record daily and per-minute directions/matrix/geocoding quotas from the key's dashboard, choose request intervals accordingly, and smoke-test a multi-day route. The default two-second spacing is process local and does not enforce a daily or global serverless quota. Caches can disappear between requests. Public Overpass and OSM tile services are best effort. The API returns explicit retryable 429/503/504 responses rather than fabricating a result.

## Frontend project (`frontend`)

Use the Vite framework preset and Node 24. Enable **Include source files outside of the Root Directory** so the root npm workspace/lock and shared contracts are included. The supplied `vercel.json` installs/builds from the monorepo root and publishes `frontend/dist` (output directory `dist` relative to project root). Set `VITE_API_BASE_URL=https://YOUR-API-DOMAIN` and redeploy; this variable is compiled into the client. Set the matching origin in backend CORS before testing. Provider and signing keys never belong in the frontend environment.

## Hosted acceptance

1. Run local CI commands and push the reviewed implementation using the repository owner's account.
2. Deploy the API and verify `/api/v1/health`; it must return provider-mode header `live`.
3. Deploy the frontend with the API origin. Verify geocoding and network CORS in a fresh browser.
4. Run short, fuel, multi-day and cycle-exhaustion routes using actual addresses; check accepted stop detours and all hours/fuel bounds. Live map conditions may legitimately block a route; record that distinctly from correctness tests.
5. Download PDF for one day and all days; compare dates/totals to the displayed sheets. Keep JSON/PDF payloads below 4 MB (the platform limit is 4.5 MB). Confirm visible OSM attribution and absent secrets in the generated client bundle.
6. Verify GitHub, hosted URL and Loom access in a reviewer/private browsing context; then replace the pending delivery entries in README.

Live key/account quotas, deployed function bundle size/cold start, provider smoke tests, reviewer visibility and Loom recording remain external checks. The prepared files do not constitute a successful deployment.
