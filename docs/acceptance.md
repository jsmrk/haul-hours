# Assessment acceptance

Local verification uses deterministic network fixtures through the real Django API and scheduler. Live-provider/hosted checks are pending a routing key and publishing account access.

| Requirement | Implementation | Evidence / demo |
| --- | --- | --- |
| Django backend, React frontend | Stateless DRF API + Vite/React npm workspace | Health/contract tests, Django check, TypeScript/build |
| Four inputs | Selected current/pickup/drop-off US places; cycle decimal 0–70 | Validation and full-stack short-trip flow |
| Real road map and directions | ORS driving-hgv GeoJSON, Leaflet + visible OSM attribution | Transport adapter tests; fixture map/itinerary selection; live smoke pending |
| Required fuel/rest stops | Bounded real Overpass POIs, actual approach/exit routes | Scheduler tests, fuel/multi-day browser flows; live availability pending |
| Fuel at least every 1,000 miles | Integer-meter independent fuel audit; 30-minute ON fueling | Boundary/detour scheduler tests and fuel browser flow |
| One hour pickup and drop-off | Distinct one-hour ON events | API timeline tests; 5h driving/7h short-trip browser/PDF totals |
| 70/8 without adverse conditions | 11/14/8 rules; 10-hour rest; 34-hour restart; cycle accounting | Duty and scheduler suites; exhausted-cycle browser flow |
| Multiple filled daily sheets | UTC timeline clipped to terminal-zone days; backend SVG geometry | Midnight/DST 23/25h conservation tests, day navigation, graph selection |
| Map/log/output agreement | Shared event and accepted road-leg IDs | Browser map → itinerary → graph selection and parsed PDF totals |
| Safe failures | Bounded deadline/calls, explicit provider errors and safe prefix | Blocked/outage browser flows; retry/budget/provider tests |
| Editing/cancellation | Abort and sequence guards; previous snapshot clearly labeled | Frontend races + real API response delayed during browser edit test |
| Exports | Selected/all-day PDF and browser print; signed 24h bounded token | Download parsed with pypdf, tamper/expiry/size tests, grayscale print check |
| Kraken-inspired shadcn design | Defined colors, fonts, 12px buttons, white surfaces, subtle shadows | Browser responsive checks at 320/375/425/640/768/1024/1280/1536; fallback fonts |
| Full TypeScript / monorepo | Strict app/e2e/tooling configs, root npm workspace and generated API types | Typecheck and contracts drift check |
| Hosted app | Two Vercel project configs | Prepared; deployment and live smoke pending |
| Shareable GitHub | Existing jsmrk/haul-hours remote, local implementation commits | Push and reviewer access pending |
| Actual 3–5-minute Loom | Four-minute script in walkthrough.md | Recording and accessible URL pending |

The implementation plan's final publishing step stays unchecked until all external deliverables are accessible. Passing fixture tests should never be presented as successful live-provider or hosted verification.

Second audit on 2026-10-02: 84 backend / 20 frontend / 10 browser tests pass, with lint, types, Django, contracts and build checks green. Additional evidence covers coincident fuel/duty limits with separate facilities, cancellation/timeouts during response-body transfer, multilingual PDF text and multiline addresses, keyboard/assistive-technology log selection, selected/all-date printing, and 1,188 fixture schedules across cycle and DST boundaries. See implementation-notes.md for fix details and unchanged external delivery gaps.
