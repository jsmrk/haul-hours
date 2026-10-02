# Haul Hours Functionality and Logic Specification

Status: approved for implementation, including the supplied design system, shadcn/ui, strict TypeScript, and a monorepo.

## Goal and source

Build the assessment's Django and React application: accept a trip, calculate a feasible driving schedule, show the actual road route and scheduled stops, and generate daily driver log sheets from that schedule. Accuracy, understandable results, and a publicly testable hosted application determine success.

Source: `/home/jess/Downloads/new-full-stack-dev-assessment.docx`. The document contains the written assessment and a branding image, but no example log sheet or application design.

The repository currently contains a README and its initial commit. There is no existing application to extend.

## Assessment requirements

- Django backend and React frontend.
- Required inputs: Current location; Pickup location; Dropoff location; Current Cycle Used (Hrs).
- Outputs: a road route map, route instructions, stop/rest information, and filled daily log sheets, including multiple sheets for longer trips.
- Use a free map API.
- Property-carrying driver, 70hrs/8days, no adverse driving conditions.
- Fueling at least once every 1,000 miles.
- 1 hour for pickup and drop-off, interpreted as one hour for each activity.
- Deliver a live hosted version, GitHub code, and a 3–5 minute Loom walkthrough of the application and code.
- The assessment evaluates output accuracy and good UI/UX. Apply the user's supplied [Kraken-inspired design system](2026-10-02-haul-hours-design-system.md).

## Decisions established with the user

| Decision | Selected behavior |
| --- | --- |
| Initial daily availability | Driver starts fully rested, with full daily driving allowances. Entered cycle usage remains used. |
| Cycle exhaustion | Automatically schedule a new 34-hour restart and continue the trip. |
| Departure | Optional departure date/time, defaulting to the current instant. |
| Fueling | 30-minute on-duty, not-driving fuel stops; trip fuel-distance counter starts at zero. |
| Stop locations | Use real truck stops/rest areas and count their road detours. Flag stretches where a suitable stop cannot be found. |
| Remaining routine decisions | User directed: "do all recommended." The defaults below are planning decisions under that instruction. |
| Visual system | Supplied Kraken-inspired white/purple system, readable neutral text, 12px buttons, and restrained shadows. |

## Recommended defaults and scope

Use a single-driver, US trip planner. Search US locations and route without international border crossings or ferries. Locations entered by the user represent truck-accessible sites. The departure location is assumed to allow the driver to wait off duty if an initial cycle restart is needed. Loading and unloading are uninterrupted and each takes 3,600 seconds; appointment windows, traffic delays, and inspections are not added to the assessment's fixed service times.

Display miles and hours/minutes. Internally calculate elapsed time in integer seconds and normalize road distances to integer meters, rounding provider totals upward. The 1,000-mile fuel threshold is exactly 1,609,344 meters. Preserve provider distances and timings per step; allocate normalization residuals so step totals equal their leg totals.

Add optional log details: driver name, carrier name/address, truck number, trailer number, shipment reference, and starting odometer. Default the log timezone to the departure location's IANA timezone; allow an explicit home-terminal timezone override. Missing details print as "Not provided"; signatures remain blank. Records are titled "Projected driver daily log" because these are schedules generated from assumptions.

Provide in-app daily sheets, printing, and a PDF containing either all days or a selected day. Keep the last form in browser session storage. The first release needs no account, database, saved-trip library, background queue, actual vehicle telemetry, signature certification, split sleeper-berth calculation, short-haul exception, or adverse-condition extension.

The [design system specification](2026-10-02-haul-hours-design-system.md) defines the exact palette, type hierarchy, components, responsive layouts, and print treatment. Use white surfaces, primary `#7132f5`, near-black `#101114`, and 12px button corners. Proprietary fonts use the supplied fallback stacks until licensed files are available. Accessible form behavior, loading/error states, map selection, and log navigation are part of this plan.

## Architecture and selected approach

Keep frontend/, backend/, contracts/, and docs/ in one private npm-workspaces monorepo. Root commands run both services, tests, contract generation, and builds; Django uses its own Python virtual environment. Strict TypeScript also covers repository tooling and frontend configuration/tests.

Choose a stateless Django API with a pure Python scheduling engine, typed provider adapters, and a React/TypeScript client. Map markers, itinerary, summary, and daily sheets all consume the same backend event timeline. React does not calculate a second schedule.

Other approaches considered: putting scheduling in React would duplicate backend validation; starting with accounts, a database, and queued jobs would add infrastructure without serving the assessment's inputs and outputs. The selected approach makes the driving rules directly testable and avoids persistent storage dependencies for the hosted assessment.

Use Python 3.12–3.14, Django 5.2 LTS (5.2.8+ on Python 3.14), Django REST Framework, HTTPX, timezonefinder/zoneinfo, and ReportLab. Use React, strict TypeScript, Vite, customized shadcn/ui Radix components, Tailwind CSS v4, Leaflet, and the Temporal polyfill for timezone-safe departure input. Resolve and lock compatible supported package versions during implementation. Django's supported-release table confirms 5.2 is an LTS series. [Django releases](https://www.djangoproject.com/download/)

Use openrouteservice for geocoding and `driving-hgv` directions, Overpass/OpenStreetMap for stop discovery, and OpenStreetMap raster tiles through Leaflet. Keep routing credentials on the backend. Heavy-vehicle routing is supported, but weight/height/length restrictions require supplied vehicle parameters; the assessment provides none, so the route summary must state that vehicle dimensions have not been checked. [Services](https://openrouteservice.org/services/), [routing options](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/routing-options)

## User flow and outputs

1. Enter and select each location from suggestions. A changed location invalidates the previous selection.
2. Enter cycle usage from 0 through 70 inclusive, with at most two decimal places. Optionally set departure and log details.
3. Submit once. Show an honest loading message while providers and the scheduler run; allow cancellation of the browser request and ignore stale responses.
4. Show trip distance, driving time, elapsed time, pickup arrival, drop-off arrival, delivery completion, fuel-stop count, rest count, and cycle-restart count.
5. Show current location → pickup → drop-off road geometry, including detours, and distinct real stop markers. Selecting an itinerary event focuses its marker or road segment; selecting a marker reveals that same event.
6. Show ordered turn instructions alongside driving legs. Stop details include name, coordinates/location, arrival/departure, activity, duty status, duration, and the reason for stopping.
7. Navigate daily sheets by date. Print or download a selected day or all days.
8. Editing inputs marks the previous results as belonging to the previous trip. Recalculation replaces the complete result atomically.

Drop-off arrival and delivery completion are distinct: completion includes the final one-hour unloading activity. Finish the itinerary after unloading; off-duty padding to finish the last sheet does not extend trip elapsed time.

## Duty rules

For the selected ordinary property-carrying rules: drive at most 11 hours after a qualifying 10-hour rest; do not drive outside the 14-hour window beginning with the first on-duty/driving event; require a 30-minute non-driving interruption before driving beyond eight cumulative driving hours since the last qualifying interruption. Short breaks do not pause the 14-hour window. The cycle includes driving and on-duty work. A 34-hour off-duty restart restores cycle availability. [FMCSA summary](https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations)

Represent duty status as OFF, SB, D, or ON. Use OFF for planned short breaks, 10-hour rests, and 34-hour restarts; do not assume sleeper-berth use. Use ON for pickup, drop-off, and fueling. Any uninterrupted non-driving interval of at least 1,800 seconds, including ON service, resets the break-driving counter.

The 14-hour and 70-hour rules restrict further driving, rather than prohibiting every non-driving task. A service event may finish after the driving window or take cycle usage above 70; record its full duration and prevent further driving until the appropriate reset. The final unload does not cause an unnecessary post-trip restart. Before selecting a fuel-only stop that cannot host a long rest, reserve enough cycle time to fuel and leave for a reachable rest site.

Engine state contains current UTC instant, duty-window start, driving since the last daily reset, driving since the last qualifying interruption, cycle-used seconds, uninterrupted non-driving seconds, uninterrupted off-duty seconds, and meters since fuel. Daily rests clear daily driving/window and break counters, leaving cycle usage unchanged. Cycle restarts also clear cycle usage. Midnight only splits sheets; it does not reset driving clocks.

Only an aggregate cycle input is available. Do not invent an eight-day distribution or promise exact recap availability. Keep usage conservatively accumulated until a scheduled restart. This implements the agreed restart policy; it may schedule more rest than a driver with known prior daily records would need.

## Routing and real stop selection

First get the two mandatory road legs, skipping provider calls for co-located waypoints while preserving both service events. Use route step durations to estimate where constraints approach; do not substitute a constant highway speed.

Discover candidates around the upcoming constraint and progressively earlier route positions. Query bounded corridor windows rather than downloading a nationwide POI collection. Candidate tags identify fuel, truck access, service/rest areas, and truck parking; exclude explicit private/no-access/no-HGV locations. Long rests require mapped truck parking or a truck-stop/rest-area category with parking evidence. A fuel pump alone is not an overnight site. The UI states that live space availability and opening times are not verified.

For each decision:

1. Calculate the next driving boundary: daily allowance, window end, break allowance, cycle availability, fuel range, or mandatory waypoint, whichever comes first.
2. If the next mandatory waypoint is reachable, drive there and apply its service activity. Loading may replace an otherwise needed short break.
3. Otherwise find real sites before the boundary with the needed capabilities. Rank by useful forward progress, then added travel time, then stable provider ID.
4. Use the provider's road matrix to prune candidates, then fetch actual directions to verify the selected approach and onward route. Count all approach, return, and onward travel; never use straight-line distance as a feasibility test.
5. Confirm future reachable stopping opportunities before committing to a site. Try up to three verified candidates; backtrack up to three previous stop decisions if necessary. This is a bounded feasible-route search, not a guarantee of the globally fastest schedule.
6. Emit driving and stop events using the accepted directions, advance clocks and fuel distance, and repeat. The geometry and instructions returned to the client are assembled from these same accepted road edges; do not reroute the entire trip after timing it.

A 30-minute fuel event replaces a separate short break. A long rest replaces a pending short break. Co-located fueling and a long rest remain sequential: 30 minutes ON followed by 10 or 34 hours OFF. A 34-hour restart subsumes a daily rest; do not add another ten hours. Resting does not reset fuel mileage. Stop early if that is necessary to reach an actual site within limits.

If discovery fails or the bounded search finds no feasible sequence, return a blocked result with a reason and safe computed prefix. Distinguish "no feasible stop found in available map data/search budget" from an assertion that no stop exists. Show no complete ETA or complete-trip PDF for that result. Never fabricate a named stop or emit a successful schedule containing an over-limit driving event.

openrouteservice currently limits a driving directions request to 6,000 km and 50 waypoints. Request the two base legs separately; return a clear route-limit error if either exceeds the provider limit. Accepted stop edges are fetched separately. [API restrictions](https://openrouteservice.org/restrictions/)

## Timeline and daily sheets

Each event has a stable ID, kind, duty status, UTC start/end, start/end location, road distance, driving-leg reference, reasons, and optional real POI reference. Separate display labels from enum values. Events must be ordered, positive-duration, contiguous, and non-overlapping; co-located service remains a positive-duration ON event.

Split events at home-terminal local day boundaries. Store elapsed durations in UTC so travel across timezone borders cannot add or remove driving time. Use the same IANA timezone throughout the trip, including its daylight-saving changes. FMCSA guidance requires UTC storage and the home-terminal time standard, including daylight saving when in effect. [Timezone guidance](https://www.fmcsa.dot.gov/hours-service/elds/how-should-time-zone-offset-utc-handle-daylight-savings-time-1)

Normal sheets have 24 hours, four duty rows, hourly labels, 15-minute guide marks, a stepped duty trace, daily status totals, planned miles, and remarks for transitions and stops. Keep precise event times rather than rounding events to grid marks. Show SB with zero hours when unused. Include location and reasons in remarks. [FMCSA log guidance](https://ai.fmcsa.dot.gov/NewEntrant/MC/Content.aspx?nav=Logs)

For daylight-saving transition dates, use a chronological 23/25-hour axis with skipped/repeated hours and UTC offsets explicitly labeled. Totals equal that local day's actual elapsed length; never force them to 24 hours. Allocate a split driving edge's miles using its step-level distance/time profile, with residual allocation preserving total trip miles.

Pad before departure and after delivery completion with OFF, explicitly marked "Assumed off duty outside planned trip." These assumptions fill the sheets without inventing prior on-duty records. A delivery completed exactly at midnight belongs to the preceding interval's sheet; do not add an empty next-day sheet. Include completely off-duty intermediate dates during a restart.

React renders sheets as SVG. The backend returns graph coordinates/ticks as part of the log model, and ReportLab uses that same model for PDF drawing. PDF export receives a signed, expiring log bundle produced with the result, avoiding a second routing calculation or a database. Optional header metadata can change without changing the duty trace.

## API and operational behavior

| Endpoint | Contract |
| --- | --- |
| `GET /api/v1/health` | 200 with service and planner version; no provider request. |
| `GET /api/v1/locations?q=...&limit=5` | US suggestions: ID, label, coordinates, and IANA timezone; query length 3–200. |
| `POST /api/v1/trips/plan` | Validated locations, cycle usage, offset-aware departure, log timezone, optional metadata → complete result or explicit problem. |
| `POST /api/v1/logs/pdf` | Signed log token, validated optional metadata, optional selected date → PDF; no provider call. |

Successful planning returns request echo, assumptions, summary, accepted route legs/instructions, events, daily logs, warnings, planner version, and an export token. Errors use `code`, `message`, `field_errors`, `retryable`, and optional `safe_prefix`; clients must branch on codes rather than matching prose.

Use 400 for invalid input; 409 for a blocked feasible-stop search; 413 for request/result size limits; 422 for provider route limits/unreachable roads; 429 for provider throttling; 503 for unavailable providers; 504 for the planning deadline. Bound JSON request and successful response to 4 MB; PDF export to 4 MB. PDF tokens expire after 24 hours; distinguish tampering (400) from expiry (410).

Use a 180-second total planning deadline, a 190-second frontend timeout, at most 64 planned stops, 160 external requests per plan, 100 POIs per discovery window, five matrix candidates per batch, three verified candidate attempts per decision, and three decisions of backtracking. Fail with a search/deadline problem when exhausted. Timeouts: directions/matrix 10 seconds; POI search 15 seconds. A single retry for idempotent transient failures may occur only inside the same deadline; honor Retry-After without retry storms.

Cache provider results opportunistically in bounded in-process memory: routes/matrices 24 hours; POIs 24 hours; geocodes seven days. This cache is expendable across serverless instances and is not a global quota guarantee. Configure outgoing rate limits to the actual free-key allowances during deployment, respect upstream 429s, and use provider/dashboard limits for aggregate protection. [Overpass resource guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)

Tiles load directly in the browser with visible attribution, normal browser caching, no bulk prefetch, and a configurable HTTPS tile URL. [Tile policy](https://operations.osmfoundation.org/policies/tiles/)

## Delivery and acceptance

Deploy React and Django as two Vercel projects from the monorepo, with the frontend calling the backend through an explicit API base URL and narrowly configured CORS. The stateless API needs stable secrets but no persistent filesystem. Vercel documents native Django support; its Fluid Compute Python Hobby duration currently allows up to 300 seconds, above the selected application deadline. Verify these limits when deploying. [Django hosting](https://vercel.com/docs/frameworks/full-stack/django), [function limits](https://vercel.com/docs/functions/limitations)

Acceptance requires deterministic tests for duty boundaries, cycles, fuel limits, detours, midnight and DST; provider-contract tests using fixtures; UI tests for stale requests, validation, event selection and export; and hosted smoke checks for short, multi-day, fuel-stop, and near-exhausted-cycle trips. Map, itinerary, summaries, SVG, and PDF must agree.

Prepare setup instructions, environment examples, documented assumptions, provider attribution, live/GitHub links, and a timed 3–5 minute Loom outline covering inputs, route/stops, daily logs, the scheduling engine, and tests. Final aesthetic acceptance checks the supplied design system across the specified widths and print/PDF layouts.

Implementation prerequisites are an openrouteservice free API key and Vercel/GitHub access for publishing. Preparing code and deployment configuration can proceed without publishing credentials; hosting and recording the actual Loom remain execution deliverables.
