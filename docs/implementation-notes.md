# Implementation decisions and pending delivery

The approved functional/design plan is implemented locally in a Django + React monorepo using customized shadcn/ui and strict TypeScript. Build and local verification are distinct from external publishing.

1. Explicit fixture mode permits full-stack browser tests and a local demo without a routing key. It never replaces a failed live provider, displays Test data, adds a response warning and is refused on hosting. Cost if misunderstood: illustrative routes could be treated as actual directions.
2. Live provider/account quota checks, hosted frontend/API, GitHub push/reviewer visibility and the actual Loom remain pending external access. Configuration, acceptance criteria and a four-minute script are prepared. Cost: the final assessment delivery remains incomplete until these checks succeed.
3. PDF header values and dense remarks continue in remarks/extra pages instead of being discarded. Normal daily sheets fit one page. Cost: a dense day may occupy additional pages.

Other implementation details: Django 5.2's compatible patch supports the host's Python 3.14 while domain code remains compatible with 3.12. TypeScript 7 uses relative path aliases because baseUrl was removed. Signed exports validate their signature before bounded decompression, and carry a signed 24-hour expiry. Local process caches/pacing are expendable and do not provide a distributed quota gate. No proprietary Kraken font binaries are bundled.

Review findings and final verification evidence will be appended here before handoff.

Local verification on 2026-10-02: 70 backend tests, 15 frontend tests and 9 full-stack Playwright tests passed. Ruff, strict TypeScript, Django check, schema drift check and Vite build passed. Browser checks covered 320–1536px, explicit fixture labeling, focus, no page overflow and one-page normal sheet printing. The Vite build reports a non-failing main chunk warning (~707 kB minified / 217 kB gzip); the map is loaded separately.

## Final review

A fresh reviewer found no illegal driving or accepted fuel-only exit dead end. Three reproduced defects were fixed with failing regression tests before the code change: Overpass HTTP-200 runtime errors were wrongly cached as no stops; a leading zero-duration routing step lost a meter in log partitions; and fractional default departures lost a second from daily totals. The latter two were upgraded from Minor to Important because normal inputs could produce inconsistent records. Departure is normalized to whole seconds at the API boundary; cumulative distance starts at zero; partial/error stop responses return retryable 503 without caching. Tests cover midnight and both DST transitions.

Decisions on review scope: live quotas/hosting/publishing/Loom remain pending; the implementer verified browser layouts and printing directly; bounded search, parking evidence, conservative recap and process-local pacing retain their approved/documented limitations. Costs: an existing feasible route can be missed, a mapped facility can be unavailable, and upstream quotas can still be exceeded across processes. Additional arbitrary malformed upstream shapes and extreme calendar inputs were not broadened in this pass; rare unsupported inputs may receive a generic API error. The non-failing bundle-size warning remains a performance improvement for later.

Final verification after fixes on 2026-10-02: 77 backend tests, 15 frontend tests and 9 browser tests passed, with lint/typecheck/Django/contracts/build checks green. Local fast-forward integration places the implementation in the original user workspace; the feature branch/worktree stay available because external delivery remains pending. Nothing has been pushed to GitHub.

## Additional double check

The requested second audit found and fixed three further issues:

- When fuel and duty limits coincide, an earlier fuel-only site can now lead to separate reachable parking. Daily and cycle regressions complete through actual road edges and pass the independent duty audit; fuel-only dead ends remain rejected.
- Frontend request deadlines and cancellation now cover response-body consumption. Tests exercise stalled location, planning and PDF responses after headers arrive, cancellation during a body read, and malformed JSON.
- PDF details and location remarks use embedded licensed font subsets for Latin, Greek, Cyrillic, Chinese and Japanese glyphs. Width-based wrapping preserves long values. Newline, tab and CRLF addresses are normalized before measurement. Characters outside the font coverage produce an explicit export error, with browser printing available, rather than silently replacing names. Font provenance and Apache license are included beside the backend assets.

A fresh reviewer checked the fixes and found no remaining concrete issues. The initially suspected graph accessibility issue was not confirmed: Chrome's complete accessibility tree exposes the focusable event buttons despite their omission from the compact snapshot. A browser test now verifies their exposure and Enter/Space selection.

Verification on 2026-10-02: 84 backend tests, 20 frontend tests and 10 browser tests pass; Ruff, strict TypeScript, Django check, contract drift and production build pass. An additional deterministic audit checked 1,188 complete fixture schedules across three route lengths, eleven cycle values, six terminal zones and six departure times. All preserve planned duty seconds and distance across their daily sheets, including 264 spring and 264 fall transition days. Browser print selection shows one selected date or all three restart dates as requested; the resulting three-page print PDF and multilingual backend PDF were visually inspected.

Live-provider/account quotas, hosted URLs, GitHub publishing/reviewer visibility and an actual Loom recording remain unverified and pending external access. The existing main-bundle size warning remains non-failing.

The fixes are integrated into local `main` at `d8ba0a7`; fresh checks in that workspace also pass 84 backend / 20 frontend / 10 browser tests and all build/contract/type checks. `npm audit --omit=dev` reports zero known vulnerabilities and `pip check` reports no broken requirements. A Python vulnerability scan did not run: two attempts to install its separate audit tool stalled and were terminated. Dependency consistency is verified; no Python vulnerability verdict is claimed.
