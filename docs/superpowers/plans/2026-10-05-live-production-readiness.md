# Live Production Readiness Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement and verify this plan in the existing isolated workspace.

**Goal:** Make live trip planning, stop discovery, logs and export reliable enough to deploy, with explicit handling of upstream outages.

**Architecture:** Keep the existing stateless Django API and typed React application. Use DOT truck-space inventory for rest facilities and the existing ORS key plus original OSM records for fuel/access evidence. Retain configurable Overpass with small queries and bounded failover as an optional adapter. Keep truck routing and independent duty audits authoritative.

**Tech Stack:** Django, httpx, React, strict TypeScript, shadcn/ui, Vitest, pytest, Playwright, Vercel.

**Spec:** Existing approved application plan, `2026-10-02-haul-hours-implementation.md`; user's request to fix all live functionality for production deployment.

## Global Constraints

- No fixture substitution, invented stops, car routing fallback, or unaudited completion.
- Preserve 180-second planning deadline, request budget, 4 MB bounds and signed PDF snapshots.
- Keep credentials server-only and preserve existing local environment files.
- Preserve Kraken tokens, shadcn components and skeleton loading states.
- Prepare existing Vercel deployment; external publishing is a separate final action.

## Review Focus

- Timeouts, malformed JSON and Overpass HTTP-200 runtime errors must fail over without caching partial data.
- Rate limits, expired budgets and invalid credentials must remain explicit and must not trigger unbounded retries.
- A successful empty stop query must remain distinguishable from an unavailable service.
- Production configuration must reject missing secrets, keys, hosts and frontend origins.
- Retry controls must resubmit the current form and retain loading/cancellation behavior.

## Tasks

- [x] Add regression tests and implement bounded stop-provider failover, smaller queries and specific error messages in `backend/planner/routing/overpass.py`, `http.py` and `api/views.py`.
- [x] Replace unreliable public Overpass as the default with real DOT/ORS/OSM stop evidence in `backend/planner/routing/live_stops.py`. Disclose inventory age and require actual road routes for all accepted stops.
- [x] Add production-setting regression tests, HTTPS/security configuration and configurable provider endpoints in `backend/config/settings.py`; update environment examples and deployment instructions.
- [x] Test and add a retry button for transient errors in `frontend/src/App.tsx`.
- [x] Add a TypeScript live smoke command covering real short, overnight, fuel and cycle-restart trips; audit timelines and export PDFs using the same server settings.
- [x] Run the complete suites, strict checks, production build and deploy checks. Verify the previously failing Harrisonburg trip using the actual key, review changes, merge locally and restart the live preview.

## Completion Evidence (2026-10-05)

- 126 backend tests, 26 frontend tests and 12 browser tests pass; lint, strict TypeScript, API checks and contract consistency pass.
- Local and Vercel-mode HTTPS frontend builds pass. Django's production deploy check reports no errors; HSTS subdomain/preload warnings reflect the deliberate policy documented in `docs/deployment.md`.
- All four real-provider smoke scenarios pass, including single/all-day PDFs. The live Harrisonburg browser flow completes with two daily logs and the disclosed inventory limitation.
- Independent read-only review approved merging after fixing HTTP 410 handling for deleted fuel records. Regression tests cover both removed and nonexistent records without hiding the next valid station.
- Changes merged locally; live API runs on port 8010 and frontend on port 5180. A fresh short-trip and PDF smoke check passes against the merged app.
- Hosted bundle/cold-start/CORS/smoke checks, account-wide quotas and reviewer/Loom delivery require external deployment or account information and remain explicitly recorded in `docs/deployment.md`. Current parking availability requires confirmation at the facility; historical inventory is disclosed, not treated as current occupancy.
