# Haul Hours Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Implementation is authorized. Execute the tasks continuously and record verification in the execution ledger.

**Goal:** Build the assessment's trip planner with actual road routing, feasible fuel/rest stops, and matching daily driver logs.

**Architecture:** Django owns validation, provider access, scheduling, and log generation. A pure Python duty engine supports a stop-aware scheduler; React consumes its one event timeline for maps, itinerary, summaries, SVG sheets, and PDF export. The application is stateless. One npm-workspaces monorepo holds the frontend, Django backend, contracts, and strict TypeScript tooling; frontend and API deploy separately.

**Tech Stack:** Python 3.12–3.14; Django 5.2 LTS (5.2.8 or later for Python 3.14); Django REST Framework; HTTPX; timezonefinder/zoneinfo; ReportLab; React; strict TypeScript; Vite; shadcn/ui (Radix); Tailwind CSS v4; Leaflet; Temporal polyfill; pytest; Vitest/Testing Library; Playwright. Lock compatible supported versions during setup.

**Spec:** [Functionality and logic specification](../specs/2026-10-02-haul-hours-design.md) and [Kraken-inspired design system](../specs/2026-10-02-haul-hours-design-system.md). Read both before implementing; they own behavior, assumptions, visual requirements, and source references.

## Global Constraints

- Django backend and React frontend in one monorepo. Strict TypeScript covers frontend, tests, configuration, and repository tooling; Django remains Python.
- Use customized shadcn/ui components with Tailwind v4 and CSS semantic tokens; preserve accessible component behavior.
- Required inputs: Current location; Pickup location; Dropoff location; Current Cycle Used (Hrs).
- Property-carrying driver, 70hrs/8days, no adverse driving conditions.
- Fueling at least once every 1,000 miles.
- 1 hour for pickup and drop-off, interpreted as one hour for each activity.
- Daily drive limit: 39,600 seconds; driving window: 50,400 seconds; break threshold: 28,800 driving seconds; qualifying interruption: 1,800 seconds.
- Daily reset: 36,000 consecutive off-duty seconds; cycle restart: 122,400 consecutive off-duty seconds; cycle driving limit: 252,000 on-duty/driving seconds.
- Fuel event: 1,800 seconds ON; fuel-distance limit: 1,609,344 meters; initial fuel distance: zero.
- Driver starts fully rested. Keep entered cycle usage. Schedule automatic cycle restarts; do not invent prior-day recap records.
- Optional departure defaults to the current instant; one IANA home-terminal timezone controls every sheet.
- Use real stopping places and road detours; successful results cannot contain unverified over-limit driving.
- Trip completion includes final unloading. Off-duty sheet padding does not extend the trip.
- 180-second planning deadline; 190-second client timeout; 64 stops; 160 external calls; 100 POIs/window; five matrix candidates; three candidate attempts; three decisions of backtracking.
- Directions/matrix timeout: 10 seconds; POI timeout: 15 seconds; at most one deadline-bounded transient retry.
- Provider driving request limit: 6,000 km; waypoint limit: 50. Validate each base leg independently.
- Export token lifetime: 24 hours. Bound JSON request and successful response to 4 MB; PDF export to 4 MB.
- White surfaces; primary `#7132f5`; dark/deep variants `#5741d8`/`#5b1ecf`; text `#101114`; borders `#dedee5`.
- All buttons use a 12px radius. Use the supplied display/body font stacks and the exact type/spacing/shadow tokens in the design system specification.
- Use `#686b82` for readable secondary text; reserve `#9497a9` for inactive/decorative content. Brand values remain within the supplied palette.
- Responsive breakpoints: 375px, 425px, 640px, 768px, 1024px, 1280px, 1536px. No page-level horizontal overflow; logs may use a labeled internal scroll region.
- Final aesthetic acceptance checks the supplied design system across the specified widths and print/PDF layouts.

## Review Focus

1. A cycle near 70 hours plus loading/fueling must never allow another driving event without sufficient availability or a restart (Tasks 3–4).
2. A real fuel stop may be reachable while its exit detour or required onward rest is unreachable; the selected full sequence must fit (Task 4).
3. Midnight and DST must preserve elapsed duty time, event continuity, and all road miles, with 23/25-hour sheets where appropriate (Task 5).
4. Missing/limited providers must produce honest blocked or retryable results, rather than fabricated stops or an apparently complete trip (Tasks 2, 4, 6).
5. Fast location edits, resubmissions, and expired export tokens must never mix different trips' maps, sheets, or PDF downloads (Tasks 7–8).

## File structure and ownership

```text
package.json, package-lock.json, tsconfig.tools.json
scripts/{backend.ts,generate-contracts.ts}
backend/
  manage.py, pyproject.toml, requirements.txt, requirements-dev.txt
  config/{settings.py,urls.py,wsgi.py}
  planner/
    contracts.py, errors.py, constants.py
    duty/{state.py,transitions.py,limits.py,audit.py}
    routing/{contracts.py,ors.py,overpass.py,cache.py,geometry.py}
    scheduling/{candidates.py,scheduler.py,summary.py}
    logs/{days.py,graph.py,pdf.py,tokens.py}
    api/{serializers.py,views.py,urls.py}
    management/commands/export_schema.py
  tests/
    conftest.py, fixtures/
    test_contracts.py, test_providers.py, test_duty.py
    test_scheduler.py, test_logs.py, test_pdf.py, test_api.py
frontend/
  package.json, vite.config.ts, tsconfig.json, index.html
  src/{main.tsx,App.tsx}
  src/styles/{tokens.css,global.css}
  src/components/ui/{button.tsx,badge.tsx,field.tsx,card.tsx,input.tsx,...}
  src/features/trip/
    contracts.generated.ts, api.ts, departure.ts, useTripPlanner.ts
    TripForm.tsx, LocationField.tsx, TripResults.tsx
    RouteMap.tsx, Itinerary.tsx, TripSummary.tsx
    DailyLogSheet.tsx, LogNavigation.tsx, ExportControls.tsx
    trip.test.tsx, departure.test.ts, logs.test.tsx
  e2e/trip-planner.spec.ts
contracts/trip.schema.json
.github/workflows/ci.yml
docs/{deployment.md,walkthrough.md,acceptance.md}
```

Add package initializers and focused test fixtures as needed. Keep each module's ownership as listed; avoid putting provider, scheduling, and rendering logic into views or React components.

## Task 1: Establish contracts and a running health endpoint

**Files:** Create backend configuration/dependency files, `planner/{contracts.py,constants.py,errors.py}`, `planner/api/{urls.py,views.py}`, `tests/{conftest.py,test_contracts.py}`, frontend Vite/TypeScript entry files, `frontend/src/styles/{tokens.css,global.css}`, and `.env.example` files.

**Interfaces:**

- `Location(id: str, label: str, longitude: float, latitude: float, timezone: str)`.
- `TripRequest(current_location: Location, pickup_location: Location, dropoff_location: Location, cycle_used_hours: Decimal, departure_at: datetime, log_timezone: str, metadata: LogMetadata)`.
- `LogMetadata(driver_name: str | None, carrier_name: str | None, carrier_address: str | None, truck_number: str | None, trailer_number: str | None, shipment_reference: str | None, starting_odometer_miles: Decimal | None)`.
- `DutyEvent(id: str, kind: EventKind, status: DutyStatus, start_at: datetime, end_at: datetime, start_location: Location, end_location: Location, distance_m: int, driving_leg_id: str | None, reasons: tuple[str, ...], poi_id: str | None)`.
- Enums: duty `OFF/SB/D/ON`; event `drive/pickup/dropoff/fuel/break/daily_rest/cycle_restart`.
- `PlanningProblem(code: str, message: str, retryable: bool, field_errors: dict, safe_prefix: tuple[DutyEvent, ...])`.
- Produce `GET /api/v1/health` with `{"status":"ok","planner_version":"1"}`. No provider or database access.

- [ ] **Step 1: Write failing contract and health tests.**

  `test_health_is_stateless` asserts status 200 and exact response above. `test_contract_round_trip` asserts offset-aware times remain the same UTC instants, enum values remain stable, and cycle `"69.50"` survives serialization as a decimal string. `test_required_assessment_fields` asserts the four required fields are present in the request contract.

- [ ] **Step 2: Run the tests and confirm missing-contract/endpoint failures.**

  Run: `cd backend && python -m pytest tests/test_contracts.py -q`. Expected: failing tests for missing application contracts/health response; fix tooling issues before treating a failure as meaningful.

- [ ] **Step 3: Implement the contracts and foundation.**

  Define the constants in Global Constraints, UTC-aware immutable domain records, `LogMetadata`, explicit errors, and health routing. Configure Django without sessions, admin, auth, or persistent trip models. Configure private npm workspaces with frontend named @haul-hours/web, one root package-lock, root dev/test/typecheck/build commands, and TypeScript scripts for Python and contract tooling. Enable strict, allowJs:false, noUncheckedIndexedAccess, and exactOptionalPropertyTypes in application and tooling configs. Initialize shadcn/ui Radix components with Tailwind v4, CSS variables, and @ aliases; map semantic tokens to the supplied design values. Keep Python dependencies in the backend virtual environment. Scaffold React with a health-state view and import `global.css`/`tokens.css`. Define the exact color, typography, spacing, radius, shadow, and breakpoint tokens from the design system specification; use the supplied font fallbacks. Lock dependencies and record development commands.

- [ ] **Step 4: Verify both applications run.**

  Run the contract tests, `python manage.py check`, and `cd frontend && npm run build`. Expected: passing contracts, no Django configuration issues, and a successful frontend build.

- [ ] **Step 5: Commit the task deliverable.** Stage only Task 1 files; commit as `chore: establish planner contracts and application foundation`.

## Task 2: Implement normalized map and stop providers

**Files:** Create `planner/routing/{contracts.py,ors.py,overpass.py,cache.py,geometry.py}`, `tests/test_providers.py`, and provider response fixtures.

**Interfaces:**

- `RoadStep(instruction: str, distance_m: int, duration_s: int, geometry: tuple[Coordinate, ...])`; `Coordinate = tuple[float, float]` in longitude/latitude order.
- `RoadLeg(id: str, origin: Location, destination: Location, steps: tuple[RoadStep, ...], distance_m: int, duration_s: int)`.
- `StopPlace(id: str, location: Location, supports_fuel: bool, supports_short_break: bool, supports_long_rest: bool, evidence: dict[str, str])`.
- `StopSearch(anchors: tuple[Coordinate, ...], radius_m: int, needs_fuel: bool, needs_long_rest: bool)`.
- `ProviderBudget(deadline_monotonic: float, remaining_calls: int)` passed to every external operation.
- `RoutingProvider.search_locations(query: str, limit: int, budget: ProviderBudget) -> tuple[Location, ...]`.
- `RoutingProvider.route(origin: Location, destination: Location, budget: ProviderBudget) -> RoadLeg`.
- `RoutingProvider.matrix(origin: Location, destinations: tuple[Location, ...], budget: ProviderBudget) -> tuple[tuple[int, int] | None, ...]`, returning meters/seconds or unreachable.
- `StopProvider.find_candidates(search: StopSearch, budget: ProviderBudget) -> tuple[StopPlace, ...]`.
- `point_at_elapsed(leg: RoadLeg, elapsed_s: int) -> Coordinate`; `distance_at_elapsed(leg: RoadLeg, elapsed_s: int) -> int`. Both conserve normalized step totals.

- [ ] **Step 1: Write failing provider-contract tests.**

  Fixtures assert longitude/latitude order; GeoJSON/step totals; missing/null matrix entries; skipped route requests for co-located points; US/border/ferry options; truck profile selection; invalid JSON; timeouts; 429/Retry-After; and bounded cache hits. Assert a fuel place with `hgv=no` is excluded, and a fuel-only POI without parking evidence is not marked as a long-rest site. Assert no API key appears in public errors.

- [ ] **Step 2: Run `python -m pytest tests/test_providers.py -q`.** Expected: meaningful failures for provider contracts not implemented.

- [ ] **Step 3: Implement the adapter methods above.**

  Use backend-only credentials and HTTPX deadlines, normalize data, resolve location timezone, and map provider failures to `PlanningProblem`. Include user-agent/attribution metadata. Overpass queries use bounded circles/corridor anchors and tag evidence; deduplicate by provider ID and keep at most 100 candidates. Implement the spec's cache lifetimes and bounded retry rules. Provide a fixture-backed `RoadNetworkFake` implementing both provider protocols for later scheduler tests.

- [ ] **Step 4: Run provider tests and Django checks.** Expected: all tests pass without live network calls. With a configured key, perform one explicitly marked integration check of geocoding, a short truck route, and a bounded POI search; record provider capabilities, not guessed quota values.

- [ ] **Step 5: Commit as `feat: add routing and real stop provider adapters`**.

## Task 3: Implement and audit duty-clock transitions

**Files:** Create `planner/duty/{state.py,transitions.py,limits.py,audit.py}` and `tests/test_duty.py`.

**Interfaces:**

- `DutyState(now: datetime, window_started_at: datetime | None, daily_drive_s: int, break_drive_s: int, cycle_used_s: int, non_driving_run_s: int, off_duty_run_s: int, distance_since_fuel_m: int)`.
- `initial_state(request: TripRequest) -> DutyState`.
- `driving_allowance(state: DutyState) -> int`, the minimum remaining daily, break, window, and cycle seconds, clamped to zero.
- `apply_event(state: DutyState, event: DutyEvent) -> DutyState`; reject impermissible driving with an explicit domain error.
- `audit_timeline(request: TripRequest, events: tuple[DutyEvent, ...]) -> tuple[str, ...]`, independently checking event continuity and legal driving windows rather than calling the scheduler.

- [ ] **Step 1: Write failing duty tests with exact boundaries.**

  Assert driving is allowed up to 28,800 seconds before a break; 1,799 non-driving seconds do not reset that counter, while 1,800 do. Assert adjacent 900-second ON and 900-second OFF intervals together qualify as a driving interruption but do not daily-reset. Assert pickup/fuel ON qualify without clearing cycle usage. Assert 39,600 driving seconds and a 50,400-second window each prohibit another driving second. Assert 35,999 OFF seconds do not daily-reset; 36,000 do. Assert 122,400 OFF clears cycle usage and subsumes daily reset. Assert midnight does not reset anything.

  For a rested request with cycle `"69.50"`, assert a 3,600-second pickup produces 253,800 used seconds and no subsequent driving allowance. For final unloading, assert finishing beyond the driving window is valid and does not append rest. Independent audit must reject a deliberately injected one-second driving violation and an overlapping event.

- [ ] **Step 2: Run `python -m pytest tests/test_duty.py -q`.** Expected: missing transition/allowance failures.

- [ ] **Step 3: Implement the state operations above using UTC elapsed seconds.**

  Initialize full daily allowances without clearing cycle usage. Combine adjacent qualifying non-driving time even when its OFF/ON status changes; only uninterrupted OFF contributes to daily/cycle resets. Start the window on the first ON/D event. Record cycle work fully, even above 70, and clamp further driving availability until reset. Keep fuel distance across all rests and reset it only after fuel.

- [ ] **Step 4: Run duty and contract tests.** Expected: all specified boundaries pass; the audit detects injected defects.

- [ ] **Step 5: Commit as `feat: enforce duty clocks and timeline invariants`**.

## Task 4: Build a scheduler that reaches actual stops

**Files:** Create `planner/scheduling/{candidates.py,scheduler.py,summary.py}` and `tests/test_scheduler.py`.

**Interfaces:**

- `ScheduledTrip(request: TripRequest, road_legs: tuple[RoadLeg, ...], events: tuple[DutyEvent, ...], warnings: tuple[str, ...])`.
- `schedule_trip(request: TripRequest, routing: RoutingProvider, stops: StopProvider, budget: ProviderBudget) -> ScheduledTrip`; blocked search raises `PlanningProblem` with safe prefix.
- `rank_candidates(candidates: tuple[StopPlace, ...], needs_fuel: bool, needs_long_rest: bool, progress: dict[str, int], detour_seconds: dict[str, int]) -> tuple[StopPlace, ...]`.
- `TripSummary(pickup_arrival_at: datetime, dropoff_arrival_at: datetime, completed_at: datetime, distance_m: int, driving_s: int, elapsed_s: int, on_duty_s: int, off_duty_s: int, fuel_stop_count: int, short_break_count: int, daily_rest_count: int, cycle_restart_count: int)`.
- `summarize_trip(trip: ScheduledTrip) -> TripSummary`.

- [ ] **Step 1: Write failing complete-trip fixtures.**

  A two-hour-driving trip without needed stops has exactly 7,200 D seconds plus 7,200 ON service seconds and completes four hours after departure. Co-located current/pickup/drop-off produces two distinct service events totaling 7,200 ON seconds, zero D miles, and no unnecessary rest.

  Include scenarios for a long multi-day trip, exact 1,609,344-meter fuel range, fuel before exceeding that range including detours, a 70-used initial restart, and a near-exhausted cycle after pickup. Assert 34-hour restart is one 122,400-second event, not a restart plus another daily rest. Assert ON fuel and OFF rest remain distinct sequential events. Assert service prevents an unnecessary short break, and restart/rest days preserve fuel mileage.

  Use an asymmetric fake road network where the closest POI is unreachable or its exit is too long. Assert the scheduler chooses the feasible alternative, or returns `NO_FEASIBLE_STOP_FOUND` with no complete summary. A missing POI result must not become a fabricated named stop. Exercise bounded backtracking, exhausted budget, early stopping, and exact driving-boundary arrivals.

- [ ] **Step 2: Run `python -m pytest tests/test_scheduler.py -q`.** Expected: missing scheduler failures for the fixtures.

- [ ] **Step 3: Implement `schedule_trip` following the spec's decision loop.**

  Preserve mandatory waypoint order, use step timing for prospective boundaries, prune through matrix estimates, and verify road edges before emitting events. Check the next reachable stopping opportunity and fuel-only exit reserve. Respect candidate/search/backtracking limits. Assemble output geometry from the accepted edges, not a later reroute. Use deterministic tie-breaking and finish after unloading. Call the independent audit before returning success.

- [ ] **Step 4: Run provider, duty, and scheduler suites.** Expected: every successful fixture has an empty audit result, no fuel span above 1,609,344 meters, exact event/summary agreement, and real fixture POI references on scheduled stops.

- [ ] **Step 5: Commit as `feat: schedule trips with verified fuel and rest stops`**.

## Task 5: Generate daily log models and matching PDFs

**Files:** Create `planner/logs/{days.py,graph.py,pdf.py,tokens.py}`, `tests/{test_logs.py,test_pdf.py}`, and representative log/PDF fixtures.

**Interfaces:**

- `DailyLog(date: str, timezone: str, start_at: datetime, end_at: datetime, duration_s: int, intervals: tuple[LogInterval, ...], totals_s: dict[DutyStatus, int], distance_m: int, remarks: tuple[LogRemark, ...], graph: LogGraph)`.
- `LogInterval(event_id: str | None, status: DutyStatus, start_at: datetime, end_at: datetime, distance_m: int, assumed_outside_trip: bool)`.
- `LogRemark(at: datetime, location_label: str, note: str, event_id: str | None)`.
- `GraphTick(elapsed_s: int, label: str, utc_offset_s: int)`.
- `GraphPath(event_id: str | None, points: tuple[tuple[float, int], ...])`; each point is normalized elapsed position in [0, 1] and row index 0–3 for OFF/SB/D/ON.
- `LogGraph(ticks: tuple[GraphTick, ...], paths: tuple[GraphPath, ...])`.
- `build_daily_logs(trip: ScheduledTrip) -> tuple[DailyLog, ...]`.
- `draw_log_pdf(logs: tuple[DailyLog, ...], metadata: LogMetadata) -> bytes`.
- `sign_log_bundle(logs: tuple[DailyLog, ...]) -> str`; `verify_log_bundle(token: str, now: datetime) -> tuple[DailyLog, ...]`.

- [ ] **Step 1: Write failing daily/PDF tests.**

  Assert normal-day totals equal 86,400 seconds, graph row order is OFF/SB/D/ON, SB is zero when unused, and an event spanning midnight keeps its ID and conserved miles on both dates. Intermediate restart dates must render; midnight completion must not create an empty date. Outside-trip padding must carry its assumption flag and leave trip completion unchanged.

  For `America/New_York`, assert 2026-03-08 has 82,800 seconds and 2026-11-01 has 90,000 seconds, with labeled skipped/repeated hours. A ten-hour UTC rest crossing DST must still be exactly 36,000 seconds. Assert PDF page count equals selected sheet count, status totals/header text match the log model, missing metadata says "Not provided", and signature is blank. Assert token tampering fails and a token beyond 24 hours expires.

- [ ] **Step 2: Run `python -m pytest tests/test_logs.py tests/test_pdf.py -q`.** Expected: missing log/export failures.

- [ ] **Step 3: Implement the interfaces above.**

  Clip at timezone-aware local boundaries and derive ticks from UTC chronology. Allocate split distance from road-step profiles and residuals. Generate graph paths once, consume them in ReportLab, and preserve the projection/outside-trip labels. Use Django timestamp signing with a stable backend secret and a planner-versioned compressed payload; validate size before signing, decompression, and drawing.

- [ ] **Step 4: Run log/PDF suites and visually inspect normal, multi-day, and DST PDFs.** Expected: numerical assertions pass and every sheet has readable ticks, transitions, remarks, and metadata. Store expected fixtures; avoid brittle assertions against raw PDF binary bytes.

- [ ] **Step 5: Commit as `feat: generate projected daily sheets and signed PDF exports`**.

## Task 6: Expose the planning and export API

**Files:** Implement `planner/api/{serializers.py,views.py,urls.py}`, `planner/management/commands/export_schema.py`, `tests/test_api.py`, and `contracts/trip.schema.json`.

**Interfaces:**

- `GET /api/v1/locations?q=...&limit=5` returns `{"locations": Location[]}`.
- `POST /api/v1/trips/plan` accepts the Task 1 request fields; decimal cycle/odometer values are JSON strings and departure is offset-aware ISO 8601.
- `PlanResult(request: TripRequest, assumptions: str[], summary: TripSummary, road_legs: RoadLeg[], events: DutyEvent[], daily_logs: DailyLog[], warnings: str[], planner_version: str, export_token: str)`.
- `POST /api/v1/logs/pdf` accepts `{export_token, metadata, date?: string}` and returns `application/pdf` with a safe content-disposition filename.
- Produce `python manage.py export_schema --output ../contracts/trip.schema.json` from the API serializers, not a hand-maintained second contract.

- [ ] **Step 1: Write failing endpoint tests.**

  Assert cycle `"0"`/`"70"` accepted; negative, over-70, nonnumeric/nonfinite, or over-two-decimal input rejected with field errors. Assert coordinates, US region, timezone, departure offset and metadata are validated. Test all spec error/status mappings, including 409 safe prefix, 422 route cap, 429, 503, 504, 410 token expiry, and 413 oversize payload. Assert exported PDF uses the returned timeline token without calling routing providers. Verify changing header metadata cannot alter a duty interval.

- [ ] **Step 2: Run `python -m pytest tests/test_api.py -q`.** Expected: missing planning/export handlers or response-contract failures.

- [ ] **Step 3: Implement the endpoints and error envelopes.**

  Create request budgets at the API boundary, call adapters → scheduler → logs → signing, and serialize one consistent result. Validate provider-leg limits before expensive stop searches. Set CORS to the configured frontend origin, keep secrets out of responses, and include request IDs in server logs. The API returns a bounded complete result atomically; there is no persisted job ID. Generate the JSON Schema and add a deterministic schema-drift check to CI.

- [ ] **Step 4: Run the entire backend suite, schema generation, and Django checks.** Expected: all tests pass offline, generated schema is stable, and response fields match the spec.

- [ ] **Step 5: Commit as `feat: expose trip planning and daily log export endpoints`**.

## Task 7: Build trip input, timezone handling, and request state

**Files:** Implement frontend `contracts.generated.ts`, `api.ts`, `departure.ts`, `useTripPlanner.ts`, `TripForm.tsx`, `LocationField.tsx`, `trip.test.tsx`, and `departure.test.ts`; create `frontend/src/components/ui/{button.tsx,badge.tsx,field.tsx,card.tsx,input.tsx,...}` using the shared tokens.

**Interfaces:**

- Generate TypeScript from `contracts/trip.schema.json` with `json-schema-to-typescript`; commit the generated output and check drift.
- `searchLocations(query: string, signal: AbortSignal): Promise<Location[]>`.
- `ApiProblem` extends `Error` with `status: number`, `code: string`, `retryable: boolean`, `field_errors: Record<string, string[]>`, and optional `safe_prefix: DutyEvent[]`.
- `planTrip(request: TripRequest, signal: AbortSignal): Promise<PlanResult>`; throw `ApiProblem` carrying the structured server error.
- `resolveDeparture(localDateTime: string, timezone: string, disambiguation: 'reject' | 'earlier' | 'later' = 'reject'): string`, returning an offset-aware instant. Reject nonexistent local times even if a disambiguation choice is passed; repeated times require an explicit earlier/later selection.
- `useTripPlanner()` exposes form, selected locations, phase (`idle/loading/complete/blocked/error`), result, problem, submit/cancel/reset, and previous-result status.
- Use locally generated shadcn/ui Button, Badge, Field, Card, Input, Popover/Command, Tabs, Alert, Collapsible, and loading primitives. Customize Button default/outline/secondary to the supplied palette and add subtle/white variants; all have 12px corners. Add success/neutral Badge variants with 6px/8px corners; Card has 16px corners. Preserve Radix keyboard/focus behavior. Do not create parallel hand-built UI primitives.
- API responses start as unknown and are validated against the generated JSON Schema before narrowing to generated TypeScript types. No application-owned JavaScript/JSX, any, or ts-ignore.

- [ ] **Step 1: Write failing interaction tests.**

  Assert autocomplete is debounced 300 ms, keyboard-selectable, and ignored below three characters. Editing a selected address clears its coordinates. Default departure represents the same current instant when origin timezone changes; an explicit user-edited time is interpreted in the selected log timezone. Assert DST rejection/choice behavior. Cycle validation must match the backend.

  Simulate slow old search/planning responses after a new query/submission; assert they cannot overwrite current state. Assert double submit is disabled, cancellation is safe, blocked problems show safe-prefix information, and form restoration cannot restore a stale selected address under a different label.

- [ ] **Step 2: Run `npm run test -- trip.test.tsx departure.test.ts`.** Expected: missing UI/state/helper failures.

- [ ] **Step 3: Implement the input flow and typed API client.**

  Preserve four required assessment fields; group optional departure and log headers separately. Use Temporal plus round-trip wall-time validation, accessible labels/errors, AbortController, request sequence guards, a 190-second timeout, and session-storage form state. Apply customized shadcn/ui controls, purple primary actions, white panels, readable neutral hints, 12px buttons, and the specified form/responsive layouts. Keep computation in Django. Show useful loading and provider error messages without fabricated progress percentages.

- [ ] **Step 4: Run frontend tests, TypeScript checking, and build.** Expected: matching validation, stale-response protection, and successful compilation.

- [ ] **Step 5: Commit as `feat: add trip form and timezone-safe planning requests`**.

## Task 8: Present route, itinerary, daily sheets, and exports

**Files:** Implement `TripResults.tsx`, `RouteMap.tsx`, `Itinerary.tsx`, `TripSummary.tsx`, `DailyLogSheet.tsx`, `LogNavigation.tsx`, `ExportControls.tsx`, and `logs.test.tsx`.

**Interfaces:**

- `TripResults({result: PlanResult, selectedEventId: string | null, onSelectEvent: (id: string) => void})`.
- `DailyLogSheet({log: DailyLog, metadata: LogMetadata})`; render the backend `LogGraph` as an accessible SVG.
- `downloadLogs(result: PlanResult, metadata: LogMetadata, date?: string): Promise<void>`; export the snapshot whose controls the user selected, even if a new result arrives during download.
- Map, itinerary, and graph selections refer to backend event IDs; use `driving_leg_id` to select road edges.

- [ ] **Step 1: Write failing result tests.**

  Assert pickup-before-dropoff order, arrival vs completion labels, counts and totals from backend data, map/itinerary event synchronization, and preserved road detours. Test sheet navigation, normal/DST ticks, OFF/SB/D/ON labels, visible assumption remarks, one-day/all-day export selection, and print page breaks. Assert an expired token asks for recalculation and an older in-flight PDF cannot be mislabeled as the new trip's export. Assert blocked results have no complete ETA or full-trip download action.

- [ ] **Step 2: Run `npm run test -- trip.test.tsx logs.test.tsx`.** Expected: missing result rendering/export behavior failures.

- [ ] **Step 3: Implement the components above.**

  Leaflet displays accepted geometry with a purple route, distinct origin/pickup/drop-off/fuel/break/rest/restart icons, explicit legends, and visible attribution. Show stop evidence/availability limitations where they help users interpret a location. Render turn instructions from accepted legs and daily paths from backend graph data. Apply the specified white/purple workspace, summary typography, subtle selected-event panels, semantic controls, readable empty/error states, keyboard selection, PDF blobs, and print CSS. Keep duty traces and printed records dark and readable in grayscale.

- [ ] **Step 4: Run tests/build and inspect a representative complete result in a browser.** Expected: map, itinerary, summary, sheet, and PDF agree; mobile controls and print layout remain usable.

- [ ] **Step 5: Commit as `feat: display synchronized route and daily log outputs`**.

## Task 9: Verify the whole application and prepare assessment delivery

**Files:** Create `frontend/e2e/trip-planner.spec.ts`, `.github/workflows/ci.yml`, backend/frontend Vercel configuration, `docs/{deployment.md,walkthrough.md,acceptance.md}`, and expand `README.md`.

**Interfaces:** Produce repeatable CI commands, deployable frontend/API configurations, environment documentation, an assessment acceptance matrix, and a timed Loom script. This task uses all earlier contracts without changing scheduling rules.

- [ ] **Step 1: Write failing end-to-end acceptance cases.**

  Submit a short trip, a multi-day route, a route requiring fuel, and a cycle-exhaustion route against deterministic provider fixtures. Assert one-hour pickup/drop-off, map/itinerary/log agreement, multi-sheet navigation, exported PDF, blocked-stop handling, and a provider outage. Download/parse one PDF to confirm its dates and totals match the visible result. Include a selected location changing during planning and preserve the correct result snapshot.

- [ ] **Step 2: Run `npm run test:e2e`.** Expected: any missing full-flow integration fails with a concrete assertion rather than setup errors.

- [ ] **Step 3: Complete deployment/CI/documentation configuration.**

  CI runs backend tests, Django checks, schema/TypeScript drift checks, frontend tests/typecheck/build, and fixture-backed Playwright. Configure two Vercel project roots, stable backend signing secret, provider key, allowed hosts/origins, API base URL, and timeout below the platform maximum. Provide `.env.example` values without secrets. Record free-key quotas from the account and configure adapter pacing accordingly. Document that process caches are expendable and upstream throttling is handled.

  README includes setup, commands, assumptions, real-stop search limitations, supported routing bounds, source links/attribution, and delivery links when available. `walkthrough.md` allocates about four minutes across input, route/stops, sheets/export, Django scheduling, React presentation, and tests. `acceptance.md` maps every assessment requirement to a demo/check.

- [ ] **Step 4: Run the complete local verification once.**

  Backend: `python -m pytest -q` and `python manage.py check`. Frontend: `npm run test -- --run`, `npm run typecheck`, `npm run build`, `npm run test:e2e`. Generate contract files and require no diff. Expected: all checks pass.

- [ ] **Step 5: Verify the supplied design system in the complete flows.**

  Verify the tokens/components established in Tasks 1 and 7–8 against the design specification. Inspect complete, loading, validation-error, and blocked flows at 375/425/640/768/1024/1280/1536px and an additional narrower mobile viewport. Check open suggestions, long location names, visible keyboard focus, 12px button radii, heading/body hierarchy, readable secondary text, map attribution, and internal sheet scrolling. Verify print/PDF grayscale legibility and layout. Use fallback fonts until licensed Kraken files are supplied; font availability does not block delivery. Preserve all event contracts and scheduling checks.

- [ ] **Step 6: Publish and validate assessment deliverables during execution.**

  With the required account access, deploy frontend/API and make the GitHub repository shareable. Run hosted smoke checks of health, autocomplete, the four representative trips, and PDF export using live providers; confirm secrets are absent from client bundles and tile attribution is visible. Record live provider failures separately from deterministic correctness tests. Record the actual 3–5 minute Loom and add the URL to README. Confirm all three deliverables are accessible to the reviewer.

- [ ] **Step 7: Commit as `chore: prepare and verify assessment delivery`** once the corresponding execution deliverables actually exist.

## Coverage and handoff

| Assessment item | Tasks |
| --- | --- |
| Django + React and four inputs | 1, 6, 7 |
| Road map, free API, route instructions | 2, 4, 8 |
| Stops/rests and long trips | 3, 4, 8 |
| Daily sheets and drawing on the log | 5, 8 |
| 70/8, fuel interval, service times | 3, 4 |
| Output accuracy and error behavior | 2–9 |
| Design/UX | Token foundation in 1; shared controls/layout in 7–8; visual acceptance in 9 |
| Hosted version, GitHub, 3–5 minute Loom | 9 |

Recommended execution is native, in the listed order: the scheduler, log model, and API share contracts, so sequential implementation makes their boundaries easier to verify. The user has authorized implementation, including shadcn/ui, strict TypeScript, and the monorepo. Hosting requires an openrouteservice key and publishing account access. The supplied Kraken-inspired design system is part of the plan; proprietary font files are optional because fallback stacks are defined. Build and verification progress is recorded in the execution ledger.
