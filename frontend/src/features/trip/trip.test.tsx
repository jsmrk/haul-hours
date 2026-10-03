import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { LocationField } from "./LocationField";
import { TripForm } from "./TripForm";
import { parseLocations, parsePlanResult } from "./validation";
import { isValidCycle, restoreForm, useTripPlanner } from "./useTripPlanner";
import type { Location } from "./contracts.generated";

const location: Location = { id: "ny", label: "New York, NY", longitude: -74, latitude: 40.7, timezone: "America/New_York" };

it("requires complete generated response contracts before rendering", () => {
  expect(() => parsePlanResult({ events: [] })).toThrow(/invalid response/i);
  expect(parseLocations({ locations: [location] })).toEqual([location]);
  expect(() => parseLocations({ locations: [{ label: "fake" }] })).toThrow(/invalid response/i);
});

it("keeps cycle validation within the server's decimal bounds", () => {
  for (const value of ["0", "70", "69.50", "0.01"]) expect(isValidCycle(value)).toBe(true);
  for (const value of ["", "-1", "70.01", "1.234", "NaN", "Infinity", "1e1"]) expect(isValidCycle(value)).toBe(false);
});

it("never restores stale coordinates beneath an edited label", () => {
  sessionStorage.setItem("haul-hours.form.v1", JSON.stringify({ current: { query: "Edited address", location } }));
  expect(restoreForm().current.location).toBeNull();
});

it("debounces location searches, ignores short queries, and supports keyboard selection", async () => {
  const user = userEvent.setup();
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ locations: [location] })));
  const change = vi.fn();
  const { rerender } = render(<LocationField label="Current location" id="current" value={{ query: "", location: null }} onChange={change} />);
  await user.click(screen.getByRole("combobox", { name: "Current location" }));
  rerender(<LocationField label="Current location" id="current" value={{ query: "ab", location: null }} onChange={change} />);
  await new Promise((done) => setTimeout(done, 320));
  expect(fetchSpy).not.toHaveBeenCalled();
  rerender(<LocationField label="Current location" id="current" value={{ query: "New York", location: null }} onChange={change} />);
  expect(fetchSpy).not.toHaveBeenCalled();
  await screen.findByRole("option", { name: /New York, NY/ });
  expect(fetchSpy).toHaveBeenCalledTimes(1);
  const input = screen.getByRole("combobox", { name: "Current location" });
  fireEvent.keyDown(input, { key: "ArrowDown" });
  fireEvent.keyDown(input, { key: "Enter" });
  await waitFor(() => expect(change).toHaveBeenCalledWith({ query: location.label, location }));
});

it("input edits cancel an active submission and an old response cannot set current results", async () => {
  let resolveResponse: ((value: Response) => void) | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise((resolve) => { resolveResponse = resolve; }));
  const { result } = renderHook(() => useTripPlanner());
  act(() => result.current.update({ current: { query: location.label, location }, pickup: { query: location.label, location }, dropoff: { query: location.label, location } }));
  let pending: Promise<void> | undefined;
  act(() => { pending = result.current.submit(); });
  expect(result.current.phase).toBe("loading");
  act(() => result.current.update({ cycleUsed: "10" }));
  expect(result.current.phase).toBe("idle");
  await act(async () => { resolveResponse?.(new Response(JSON.stringify({ nonsense: true }))); await pending; });
  expect(result.current.result).toBeNull();
  expect(result.current.phase).toBe("idle");
});

it("late address results never replace suggestions for the current query", async () => {
  const user = userEvent.setup();
  const replies: ((value: Response) => void)[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise((resolve) => { replies.push(resolve); }));
  const change = vi.fn();
  const props = { label: "Current location", id: "current", onChange: change };
  const { rerender } = render(<LocationField {...props} value={{ query: "New York", location: null }}/>);
  await user.click(screen.getByRole("combobox", { name: "Current location" }));
  await waitFor(() => expect(replies.length).toBe(1));
  rerender(<LocationField {...props} value={{ query: "Boston", location: null }}/>);
  await waitFor(() => expect(replies.length).toBe(2));
  const boston: Location = { ...location, id: "boston", label: "Boston, MA" };
  await act(async () => { replies[1]?.(new Response(JSON.stringify({ locations: [boston] }))); });
  expect(await screen.findByRole("option", { name: "Boston, MA" })).toBeVisible();
  await act(async () => { replies[0]?.(new Response(JSON.stringify({ locations: [location] }))); });
  expect(screen.queryByRole("option", { name: "New York, NY" })).not.toBeInTheDocument();
});

it("form submission points to the missing assessment inputs without a network request", async () => {
  const user = userEvent.setup();
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  function Form() { const planner = useTripPlanner(); return <TripForm planner={planner}/>; }
  render(<Form/>);
  await user.click(screen.getByRole("button", { name: "Plan my trip" }));
  expect(screen.getByText("Select a current location from the suggestions.")).toBeVisible();
  expect(screen.getByText("Select a pickup location from the suggestions.")).toBeVisible();
  expect(screen.getByText("Select a drop-off location from the suggestions.")).toBeVisible();
  expect(fetchSpy).not.toHaveBeenCalled();
});

it("lets users type directly into an invalid location field and select a suggestion without submitting", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ locations: [location] })));
  function Form() { const planner = useTripPlanner(); return <TripForm planner={planner}/>; }
  render(<Form/>);
  await user.click(screen.getByRole("button", { name: "Plan my trip" }));
  const input = screen.getByRole("combobox", { name: "Current location" });
  await user.type(input, "New York");
  expect(input).toHaveValue("New York");
  expect(input).toHaveFocus();
  expect(input).toHaveAttribute("aria-expanded", "true");
  await screen.findByRole("option", { name: "New York, NY" });
  await user.keyboard("{ArrowDown}{Enter}");
  expect(input).toHaveValue("New York, NY");
  expect(input).toHaveFocus();
  expect(input).toHaveAttribute("aria-invalid", "false");
  expect(input).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("option")).not.toBeInTheDocument();
  expect(screen.queryByText("Select a pickup location from the suggestions.")).not.toBeInTheDocument();
});
