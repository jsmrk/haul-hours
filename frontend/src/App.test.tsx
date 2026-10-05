import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import App from "./App";

it("replaces the empty workspace with trip skeletons during planning and restores it when cancelled", async () => {
  const location = { id: "pittsburgh", label: "Pittsburgh, PA", longitude: -79.9959, latitude: 40.4406, timezone: "America/New_York" };
  const selection = { query: location.label, location };
  sessionStorage.setItem("haul-hours.form.v1", JSON.stringify({ current: selection, pickup: selection, dropoff: selection, cycleUsed: "0" }));
  vi.spyOn(globalThis, "fetch").mockImplementation((url, options) => {
    if (String(url).endsWith("/health")) return Promise.resolve(new Response("{}", { headers: { "X-Haul-Hours-Provider-Mode": "fixtures" } }));
    return new Promise<Response>((_resolve, reject) => {
      options?.signal?.addEventListener("abort", () => reject(new DOMException("Cancelled", "AbortError")), { once: true });
    });
  });
  const user = userEvent.setup();
  render(<App/>);
  await screen.findByText(/Search these demo cities/);
  expect(screen.getByRole("heading", { name: "Your route will appear here" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Plan my trip" }));
  const preview = screen.getByRole("region", { name: "Trip plan preview" });
  expect(preview).toHaveAttribute("aria-busy", "true");
  expect(preview.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(3);
  expect(screen.queryByRole("heading", { name: "Your route will appear here" })).not.toBeInTheDocument();
  expect(within(screen.getByRole("status", { name: "Building your trip plan" })).getByText("Building your trip plan")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Cancel planning" }));
  await waitFor(() => expect(screen.queryByRole("region", { name: "Trip plan preview" })).not.toBeInTheDocument());
  expect(screen.getByRole("heading", { name: "Your route will appear here" })).toBeVisible();
});

it("retries a temporary provider failure using the selected locations", async () => {
  const location = { id: "pittsburgh", label: "Pittsburgh, PA", longitude: -79.9959, latitude: 40.4406, timezone: "America/New_York" };
  const selection = { query: location.label, location };
  sessionStorage.setItem("haul-hours.form.v1", JSON.stringify({ current: selection, pickup: selection, dropoff: selection, cycleUsed: "0" }));
  let attempts = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    if (String(url).endsWith("/health")) return Promise.resolve(new Response("{}"));
    attempts++;
    return Promise.resolve(new Response(JSON.stringify({ code: "STOP_DISCOVERY_UNAVAILABLE", message: "Could not look up fuel and rest stops. Please try again.", retryable: true, field_errors: {}, safe_prefix: [] }), { status: 503 }));
  });
  const user = userEvent.setup();
  render(<App/>);
  await user.click(screen.getByRole("button", { name: "Plan my trip" }));
  const alert = await screen.findByRole("alert");
  expect(within(alert).getByText(/fuel and rest stops/)).toBeVisible();
  await user.click(within(alert).getByRole("button", { name: "Try again" }));
  await waitFor(() => expect(attempts).toBe(2));
});
