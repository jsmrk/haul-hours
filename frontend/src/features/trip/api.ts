import type { DutyEvent, Location, LogMetadata, PlanResult, TripRequest } from "./contracts.generated";
import { isPlanningProblem, parseLocations, parsePlanResult } from "./validation";

const base = (import.meta.env["VITE_API_BASE_URL"] ?? "").replace(/\/$/, "");

export class ApiProblem extends Error {
  constructor(public status: number, public code: string, message: string, public retryable = false,
              public field_errors: Record<string, string[]> = {}, public safe_prefix: DutyEvent[] = []) {
    super(message);
    this.name = "ApiProblem";
  }
}

async function failure(response: Response): Promise<never> {
  let value: unknown;
  try { value = await response.json(); } catch { value = null; }
  if (isPlanningProblem(value)) {
    throw new ApiProblem(response.status, value.code, value.message, value.retryable, value.field_errors, value.safe_prefix);
  }
  throw new ApiProblem(response.status, "API_ERROR", "The planner could not complete this request. Please retry.", response.status >= 500);
}

async function request(path: string, options: RequestInit, signal: AbortSignal, timeout: number): Promise<Response> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal.aborted) controller.abort();
  signal.addEventListener("abort", cancel, { once: true });
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  try {
    const response = await fetch(base + "/api/v1/" + path, { ...options, signal: controller.signal });
    if (!response.ok) return await failure(response);
    return response;
  } catch (error) {
    if (timedOut) throw new ApiProblem(504, "CLIENT_TIMEOUT", "Planning took too long. Please try again.", true);
    if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
    if (error instanceof ApiProblem) throw error;
    throw new ApiProblem(503, "CONNECTION_FAILED", "Could not reach the planner. Check your connection and try again.", true);
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", cancel);
  }
}

export async function searchLocations(query: string, signal: AbortSignal): Promise<Location[]> {
  const response = await request(`locations?q=${encodeURIComponent(query)}&limit=5`, {}, signal, 26000);
  const value: unknown = await response.json();
  return parseLocations(value);
}

export async function usesFixtureData(signal: AbortSignal): Promise<boolean> {
  const response = await request("health", {}, signal, 5000);
  return response.headers.get("X-Haul-Hours-Provider-Mode") === "fixtures";
}

export async function planTrip(payload: TripRequest, signal: AbortSignal): Promise<PlanResult> {
  const response = await request("trips/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }, signal, 190000);
  const value: unknown = await response.json();
  return parsePlanResult(value);
}

export async function downloadLogs(result: PlanResult, metadata: LogMetadata, date?: string): Promise<void> {
  const body = { export_token: result.export_token, metadata, ...(date ? { date } : {}) };
  const response = await request("logs/pdf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }, new AbortController().signal, 30000);
  if (!response.headers.get("Content-Type")?.includes("application/pdf")) throw new Error("The export response is not a PDF.");
  const blob = await response.blob();
  const first = result.daily_logs[0]?.date ?? "trip";
  const last = result.daily_logs.at(-1)?.date ?? first;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `haul-hours-${date ?? (first === last ? first : `${first}-to-${last}`)}.pdf`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
