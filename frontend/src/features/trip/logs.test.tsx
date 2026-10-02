import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, it, vi } from "vitest";
import shortFixture from "@/test/fixtures/short-plan.json";
import restartFixture from "@/test/fixtures/restart-plan.json";
import { parsePlanResult } from "./validation";
import { DailyLogSheet } from "./DailyLogSheet";
import { LogNavigation } from "./LogNavigation";
import { Itinerary } from "./Itinerary";
import { TripSummary } from "./TripSummary";
import { ExportControls } from "./ExportControls";
import { downloadLogs } from "./api";

const result = parsePlanResult(shortFixture);
const restarted = parsePlanResult(restartFixture);

it("shows arrival and completion separately and uses backend totals", () => {
  render(<TripSummary result={result}/>);
  expect(screen.getByText("Drop-off arrival")).toBeVisible();
  expect(screen.getByText("Delivery complete")).toBeVisible();
  expect(screen.getByText("124.3")).toBeVisible();
  expect(screen.getByText("2h")).toBeVisible();
  expect(screen.getByText("4h")).toBeVisible();
});

it("itinerary selection highlights the same backend event on the log sheet", async () => {
  const log = result.daily_logs[0];
  if (!log) throw new Error("Missing test log");
  const sheet = log;
  function Harness() {
    const [selection, select] = useState<string | null>(null);
    return <><Itinerary result={result} selectedEventId={selection} onSelectEvent={select}/><DailyLogSheet log={sheet} metadata={{}} selectedEventId={selection} onSelectEvent={select}/></>;
  }
  render(<Harness/>);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /Pickup.*pickup/ }));
  expect(screen.getByRole("button", { name: "Select ON event event-0002" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getAllByText(/Assumed off duty outside planned trip/).length).toBeGreaterThan(0);
  expect(screen.getByText("Sleeper berth")).toBeVisible();
  expect(screen.getByText("Signature")).toBeVisible();
});

it("navigates every restart day without skipping off-duty sheets", async () => {
  const user = userEvent.setup();
  function Harness() {
    const [date, setDate] = useState(restarted.daily_logs[0]?.date ?? "");
    return <LogNavigation logs={restarted.daily_logs} selectedDate={date} onSelectDate={setDate}/>;
  }
  render(<Harness/>);
  expect(screen.getByRole("button", { name: "Previous day" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Next day" }));
  expect(screen.getByLabelText("Log date")).toHaveValue(restarted.daily_logs[1]?.date);
});

it("expired export tokens ask for recalculation", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ code: "EXPORT_EXPIRED", message: "This export has expired. Recalculate the trip to download its logs.", retryable: false, field_errors: {}, safe_prefix: [] }), { status: 410 }));
  const date = result.daily_logs[0]?.date ?? "";
  render(<ExportControls result={result} date={date}/>);
  fireEvent.click(screen.getByRole("button", { name: "Download this day" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/Recalculate the trip/);
});

it("an in-flight PDF keeps the clicked trip's date and token", async () => {
  let reply: ((value: Response) => void) | undefined;
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise((resolve) => { reply = resolve; }));
  const names: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function(this: HTMLAnchorElement) { names.push(this.download); });
  URL.createObjectURL = vi.fn(() => "blob:test");
  URL.revokeObjectURL = vi.fn();
  const pending = downloadLogs(result, {});
  const newer = { ...result, daily_logs: restarted.daily_logs, export_token: "new-token" };
  expect(newer.export_token).not.toBe(result.export_token);
  reply?.(new Response("%PDF-1.7", { headers: { "Content-Type": "application/pdf" } }));
  await pending;
  const init = fetchSpy.mock.calls[0]?.[1];
  expect(init?.body).toContain(result.export_token);
  await waitFor(() => expect(names).toEqual(["haul-hours-2026-10-02.pdf"]));
});
