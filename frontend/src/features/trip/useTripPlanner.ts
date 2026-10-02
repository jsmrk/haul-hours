import { useCallback, useEffect, useRef, useState } from "react";
import { Temporal } from "@js-temporal/polyfill";
import { ApiProblem, planTrip } from "./api";
import type { Location, LogMetadata, PlanResult, TripRequest } from "./contracts.generated";
import { resolveDeparture, type TimeChoice } from "./departure";
import { isLocation } from "./validation";

export interface LocationSelection { query: string; location: Location | null }
export const metadataFields = ["driver_name", "carrier_name", "carrier_address", "truck_number", "trailer_number", "shipment_reference", "starting_odometer_miles"] as const;
export interface TripFormState {
  current: LocationSelection; pickup: LocationSelection; dropoff: LocationSelection;
  cycleUsed: string; departureLocal: string; timeChoice: TimeChoice; timezoneOverride: string; metadata: LogMetadata;
}
export type PlannerPhase = "idle" | "loading" | "complete" | "blocked" | "error";
const storageKey = "haul-hours.form.v1";
const emptySelection = (): LocationSelection => ({ query: "", location: null });
export const emptyForm = (): TripFormState => ({ current: emptySelection(), pickup: emptySelection(), dropoff: emptySelection(), cycleUsed: "0", departureLocal: "", timeChoice: "reject", timezoneOverride: "", metadata: {} });

function record(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function restoreSelection(value: unknown): LocationSelection {
  if (!record(value)) return emptySelection();
  const query = typeof value["query"] === "string" ? value["query"] : "";
  const location = value["location"];
  return { query, location: isLocation(location) && location.label === query ? location : null };
}

export function restoreForm(): TripFormState {
  const initial = emptyForm();
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? "null");
    if (!record(value)) return initial;
    const metadata: LogMetadata = {};
    const savedMetadata = value["metadata"];
    if (record(savedMetadata)) for (const field of metadataFields) {
      const entry = savedMetadata[field];
      if (typeof entry === "string") metadata[field] = entry;
    }
    return { ...initial, current: restoreSelection(value["current"]), pickup: restoreSelection(value["pickup"]), dropoff: restoreSelection(value["dropoff"]), metadata,
      cycleUsed: typeof value["cycleUsed"] === "string" ? value["cycleUsed"] : initial.cycleUsed,
      departureLocal: typeof value["departureLocal"] === "string" ? value["departureLocal"] : "",
      timezoneOverride: typeof value["timezoneOverride"] === "string" ? value["timezoneOverride"] : "",
      timeChoice: value["timeChoice"] === "earlier" || value["timeChoice"] === "later" ? value["timeChoice"] : "reject" };
  } catch { return initial; }
}

export function isValidCycle(value: string): boolean {
  return /^\d+(?:\.\d{1,2})?$/.test(value) && Number.isFinite(Number(value)) && Number(value) >= 0 && Number(value) <= 70;
}

export function useTripPlanner() {
  const [form, setForm] = useState(restoreForm);
  const [phase, setPhase] = useState<PlannerPhase>("idle");
  const [result, setResult] = useState<PlanResult | null>(null);
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [resultFingerprint, setFingerprint] = useState("");
  const active = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const timezone = form.timezoneOverride || form.current.location?.timezone || "America/New_York";

  useEffect(() => { try { sessionStorage.setItem(storageKey, JSON.stringify(form)); } catch { /* Form remains usable when storage is unavailable. */ } }, [form]);
  useEffect(() => () => { sequence.current += 1; active.current?.abort(); }, []);

  const cancel = useCallback(() => { sequence.current += 1; active.current?.abort(); active.current = null; setPhase("idle"); }, []);
  const update = useCallback((patch: Partial<TripFormState>) => {
    if (active.current) { sequence.current += 1; active.current.abort(); active.current = null; setPhase("idle"); }
    setForm((previous) => ({ ...previous, ...patch }));
    setProblem(null);
  }, []);
  const reset = useCallback(() => { cancel(); setForm(emptyForm()); setResult(null); setProblem(null); setFingerprint(""); }, [cancel]);

  const submit = useCallback(async () => {
    if (active.current) return;
    const errors: Record<string, string[]> = {};
    if (!form.current.location) errors["current_location"] = ["Select a current location from the suggestions."];
    if (!form.pickup.location) errors["pickup_location"] = ["Select a pickup location from the suggestions."];
    if (!form.dropoff.location) errors["dropoff_location"] = ["Select a drop-off location from the suggestions."];
    if (!isValidCycle(form.cycleUsed)) errors["cycle_used_hours"] = ["Enter 0–70 hours, with at most two decimal places."];
    let departure = "";
    try { departure = form.departureLocal ? resolveDeparture(form.departureLocal, timezone, form.timeChoice) : Temporal.Now.instant().toString(); }
    catch (error) { errors["departure_at"] = [error instanceof Error ? error.message : "Choose a valid departure time and timezone."]; }
    const odometer = form.metadata.starting_odometer_miles;
    if (odometer && !/^\d+(?:\.\d{1,2})?$/.test(odometer)) errors["metadata"] = ["Starting odometer must be a positive decimal with at most two decimal places."];
    if (Object.keys(errors).length || !form.current.location || !form.pickup.location || !form.dropoff.location) {
      setProblem(new ApiProblem(400, "INVALID_INPUT", "Please correct the highlighted fields.", false, errors)); setPhase("error"); return;
    }
    const metadata: LogMetadata = {};
    for (const field of metadataFields) { const value = form.metadata[field]; if (value?.trim()) metadata[field] = value.trim(); }
    const payload: TripRequest = { current_location: form.current.location, pickup_location: form.pickup.location, dropoff_location: form.dropoff.location,
      cycle_used_hours: form.cycleUsed, departure_at: departure, log_timezone: timezone, metadata };
    const controller = new AbortController();
    active.current = controller;
    const version = ++sequence.current;
    setPhase("loading"); setProblem(null);
    try {
      const planned = await planTrip(payload, controller.signal);
      if (version !== sequence.current) return;
      setResult(planned); setFingerprint(JSON.stringify(form)); setPhase("complete");
    } catch (error) {
      if (version !== sequence.current || controller.signal.aborted) return;
      const issue = error instanceof ApiProblem ? error : new ApiProblem(502, "INVALID_RESPONSE", error instanceof Error ? error.message : "Planning failed. Please retry.", true);
      setProblem(issue); setPhase(issue.status === 409 ? "blocked" : "error");
    } finally { if (version === sequence.current) active.current = null; }
  }, [form, timezone]);

  return { form, timezone, phase, result, problem, update, submit, cancel, reset,
    previousResult: result !== null && (JSON.stringify(form) !== resultFingerprint || phase === "loading" || phase === "blocked" || phase === "error") };
}
