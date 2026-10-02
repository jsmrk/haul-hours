# Implementation decisions and pending delivery

The approved functional/design plan is implemented locally in a Django + React monorepo using customized shadcn/ui and strict TypeScript. Build and local verification are distinct from external publishing.

1. Explicit fixture mode permits full-stack browser tests and a local demo without a routing key. It never replaces a failed live provider, displays Test data, adds a response warning and is refused on hosting. Cost if misunderstood: illustrative routes could be treated as actual directions.
2. Live provider/account quota checks, hosted frontend/API, GitHub push/reviewer visibility and the actual Loom remain pending external access. Configuration, acceptance criteria and a four-minute script are prepared. Cost: the final assessment delivery remains incomplete until these checks succeed.
3. PDF header values and dense remarks continue in remarks/extra pages instead of being discarded. Normal daily sheets fit one page. Cost: a dense day may occupy additional pages.

Other implementation details: Django 5.2's compatible patch supports the host's Python 3.14 while domain code remains compatible with 3.12. TypeScript 7 uses relative path aliases because baseUrl was removed. Signed exports validate their signature before bounded decompression, and carry a signed 24-hour expiry. Local process caches/pacing are expendable and do not provide a distributed quota gate. No proprietary Kraken font binaries are bundled.

Review findings and final verification evidence will be appended here before handoff.

Local verification on 2026-10-02: 70 backend tests, 15 frontend tests and 9 full-stack Playwright tests passed. Ruff, strict TypeScript, Django check, schema drift check and Vite build passed. Browser checks covered 320–1536px, explicit fixture labeling, focus, no page overflow and one-page normal sheet printing. The Vite build reports a non-failing main chunk warning (~707 kB minified / 217 kB gzip); the map is loaded separately.
