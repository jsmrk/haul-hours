import assert from "node:assert/strict";
import type { Location, PlanResult, TripRequest } from "../frontend/src/features/trip/contracts.generated.js";

const base = (process.env["HAUL_HOURS_API_URL"] ?? "http://127.0.0.1:8010").replace(/\/$/, "");
const scenarios = [
  { name: "short", current: "Pittsburgh, PA", pickup: "Harrisburg, PA", dropoff: "Philadelphia, PA", cycle: "0", event: "dropoff" },
  { name: "overnight", current: "Pittsburgh, PA", pickup: "Harrisonburg, VA", dropoff: "Philadelphia, PA", cycle: "0", event: "daily_rest" },
  { name: "fuel", current: "Los Angeles, CA", pickup: "Phoenix, AZ", dropoff: "Dallas, TX", cycle: "0", event: "fuel" },
  { name: "restart", current: "Pittsburgh, PA", pickup: "Harrisburg, PA", dropoff: "Philadelphia, PA", cycle: "70", event: "cycle_restart" },
] as const;
const chosen = process.argv[2];
if (chosen && !scenarios.some((scenario) => scenario.name === chosen)) throw new Error("Use short, overnight, fuel, or restart; omit to run all four.");

async function json<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(base + "/api/v1/" + path, {
    ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(195_000),
  });
  if (!response.ok) {
    const problem = await response.json() as { code?: string; message?: string };
    throw new Error(`HTTP ${response.status} ${problem.code ?? "API_ERROR"}: ${problem.message ?? "Request failed"}`);
  }
  return await response.json() as T;
}

const health = await fetch(base + "/api/v1/health", { signal: AbortSignal.timeout(10_000) });
assert(health.ok && health.headers.get("X-Haul-Hours-Provider-Mode") === "live", "Smoke checks require a healthy live API; fixture mode does not qualify.");
const locationCache = new Map<string, Location>();
async function location(label: string): Promise<Location> {
  const cached = locationCache.get(label);
  if (cached) return cached;
  const result = await json<{ locations: Location[] }>("locations?q=" + encodeURIComponent(label));
  const found = result.locations.find((item) => item.label.startsWith(label));
  assert(found, `No live search result found for ${label}`);
  locationCache.set(label, found);
  return found;
}

for (const scenario of scenarios.filter((item) => !chosen || item.name === chosen)) {
  console.log(`Checking live ${scenario.name} trip…`);
  const payload: TripRequest = {
    current_location: await location(scenario.current), pickup_location: await location(scenario.pickup),
    dropoff_location: await location(scenario.dropoff), cycle_used_hours: scenario.cycle,
    departure_at: new Date().toISOString(), log_timezone: "America/New_York", metadata: { driver_name: "Live smoke check" },
  };
  const result = await json<PlanResult>("trips/plan", payload);
  assert(result.events.some((event) => event.kind === scenario.event), `Missing expected ${scenario.event} event`);
  assert(result.events.at(-1)?.kind === "dropoff", "Trip must finish with delivery");
  assert(result.daily_logs.length > 0 && result.road_legs.length > 0, "Route and daily logs are required");
  let distanceSinceFuel = 0;
  for (const event of result.events) {
    if (event.kind === "fuel") distanceSinceFuel = 0;
    else distanceSinceFuel += event.distance_m;
    assert(distanceSinceFuel <= 1_609_344, "Accepted route exceeds the 1,000-mile fuel bound");
  }
  for (const log of result.daily_logs) {
    assert(Object.values(log.totals_s).reduce((sum, seconds) => sum + seconds, 0) === log.duration_s, "Daily duty totals must cover the full day");
  }
  for (const date of [result.daily_logs[0]?.date, undefined]) {
    const response = await fetch(base + "/api/v1/logs/pdf", {
      method: "POST", headers: { "Content-Type": "application/json" }, signal: AbortSignal.timeout(30_000),
      body: JSON.stringify({ export_token: result.export_token, metadata: payload.metadata, ...(date ? { date } : {}) }),
    });
    assert(response.ok && response.headers.get("Content-Type")?.includes("application/pdf"), "PDF export failed");
    const bytes = new Uint8Array(await response.arrayBuffer());
    assert(new TextDecoder().decode(bytes.slice(0, 5)) === "%PDF-", "Invalid PDF bytes");
    assert(bytes.length < 4_000_000, "PDF exceeds the deployment response bound");
  }
  console.log(`PASS ${scenario.name}: ${result.daily_logs.length} daily log(s), ${result.summary.fuel_stop_count} fuel stop(s), ${result.summary.daily_rest_count} rest(s), PDFs verified.`);
}
