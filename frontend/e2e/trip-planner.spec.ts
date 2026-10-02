import { readFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { fileURLToPath, URL } from "node:url";
import { expect, test, type Page } from "@playwright/test";

async function selectLocation(page: Page, label: string, query: string, choice: string) {
  await page.getByRole("combobox", { name: label, exact: true }).click();
  await page.getByRole("combobox", { name: `Search ${label.toLowerCase()}` }).fill(query);
  await page.getByRole("option", { name: choice, exact: true }).click();
}

async function setupTrip(page: Page, destination = "Philadelphia, PA", cycle = "0") {
  await page.goto("/");
  await selectLocation(page, "Current location", "Pittsburgh", "Pittsburgh, PA");
  await selectLocation(page, "Pickup location", "Harrisburg", "Harrisburg, PA");
  await selectLocation(page, "Drop-off location", destination.split(",")[0] ?? destination, destination);
  await page.getByLabel("Current cycle used").fill(cycle);
  await page.getByRole("button", { name: "Departure & time zone" }).click();
  await page.getByLabel("Departure (optional)").fill("2026-10-02T08:00");
}

test("short trip agrees across map, itinerary, log and downloaded PDF", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await setupTrip(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByText("Your trip, mapped out.")).toBeVisible();
  await expect(page.getByText("5h", { exact: true })).toBeVisible();
  await expect(page.getByText("7h", { exact: true })).toBeVisible();
  await expect(page.getByText("OpenStreetMap", { exact: true })).toBeVisible();
  await page.getByRole("region", { name: "Trip itinerary" }).getByRole("button", { name: "Pickup Harrisburg, PA", exact: true }).click();
  await expect(page.locator(".leaflet-popup-content")).toContainText("Pickup");
  await page.getByRole("tab", { name: /Daily logs/ }).click();
  await expect(page.getByRole("button", { name: "Select ON event event-0002" }).first()).toHaveAttribute("aria-pressed", "true");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download this day" }).click();
  const download = await downloadPromise;
  const path = await download.path();
  if (!path) throw new Error("Missing PDF download");
  expect((await readFile(path)).subarray(0, 4).toString()).toBe("%PDF");
  const python = fileURLToPath(new URL("../../backend/.venv/bin/python", import.meta.url));
  const text = execFileSync(python, ["-c", "from pypdf import PdfReader; import sys; print(' '.join(p.extract_text() for p in PdfReader(sys.argv[1]).pages))", path], { encoding: "utf8" });
  expect(text).toContain("2026-10-02"); expect(text).toContain("05:00:00"); expect(text).toContain("02:00:00");
  expect(download.suggestedFilename()).toBe("haul-hours-2026-10-02.pdf");
  expect(errors).toEqual([]);
});

test("multi-day route includes fuel and rests and every day remains navigable", async ({ page }) => {
  await setupTrip(page, "San Diego, CA");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByText("Your trip, mapped out.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Daily rest/ }).first()).toBeVisible();
  await page.getByRole("tab", { name: /Daily logs/ }).click();
  const dates = await page.getByLabel("Log date").locator("option").allTextContents();
  expect(dates.length).toBeGreaterThan(1);
  await page.getByRole("button", { name: "Next day" }).click();
  await expect(page.getByText(`Day 2 of ${dates.length}`)).toBeVisible();
});

test("fuel route counts its accepted detour and on-duty fuel interruption", async ({ page }) => {
  await setupTrip(page, "Los Angeles, CA");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByRole("button", { name: /Fuel stop/ }).first()).toBeVisible();
  await expect(page.getByText(/1 fuel stops/)).toBeVisible();
  await expect(page.getByText("12h 30m", { exact: true })).toBeVisible();
});

test("exhausted cycle schedules one 34-hour restart and creates multiple sheets", async ({ page }) => {
  await setupTrip(page, "Philadelphia, PA", "70");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByRole("button", { name: /Cycle restart/ }).first()).toBeVisible();
  await expect(page.getByText(/1 cycle restarts/)).toBeVisible();
  await page.getByRole("tab", { name: /Daily logs/ }).click();
  await expect(page.getByLabel("Log date").locator("option")).toHaveCount(3);
});

test("blocked stops have a safe prefix without a complete ETA or export", async ({ page }) => {
  await setupTrip(page, "Boston, MA");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByRole("alert")).toContainText("No feasible sequence");
  await expect(page.getByText("Delivery complete", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Download all days" })).toHaveCount(0);
});

test("provider outage is explicit and preserves entered locations", async ({ page }) => {
  await setupTrip(page, "Miami, FL");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByRole("alert")).toContainText("temporarily unavailable");
  await expect(page.getByRole("combobox", { name: "Drop-off location", exact: true })).toContainText("Miami, FL");
});

test("editing a selected location cancels planning and preserves the previous snapshot", async ({ page }) => {
  await setupTrip(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByText("Your trip, mapped out.")).toBeVisible();
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/v1/trips/plan", async (route) => {
    const response = await route.fetch();
    await gate;
    await route.fulfill({ response }).catch(() => {});
  });
  await page.getByLabel("Current cycle used").fill("1");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Finding your way forward" })).toBeVisible();
  await selectLocation(page, "Drop-off location", "Miami", "Miami, FL");
  release();
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(page.getByText("Previous trip", { exact: true })).toBeVisible();
  await expect(page.getByText("7h", { exact: true })).toBeVisible();
  await page.unroute("**/api/v1/trips/plan");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByRole("alert")).toContainText("temporarily unavailable");
});

test("responsive forms, suggestions, results and printable sheets stay usable", async ({ page }, info) => {
  const widths = [320, 375, 425, 640, 768, 1024, 1280, 1536];
  const noOverflow = async () => {
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  };
  await setupTrip(page);
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    await noOverflow();
    const input = page.getByRole("combobox", { name: "Current location", exact: true });
    await input.click();
    await expect(page.getByRole("option", { name: "Pittsburgh, PA", exact: true })).toBeVisible();
    await noOverflow();
    await page.keyboard.press("Escape");
    await expect(input).toBeFocused();
    await page.keyboard.press("Tab");
    await input.focus();
    expect(await input.evaluate((node) => node.matches(":focus-visible") && (getComputedStyle(node).outlineStyle !== "none" || getComputedStyle(node).boxShadow !== "none"))).toBe(true);
  }
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByText("Your trip, mapped out.")).toBeVisible();
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    await noOverflow();
    await expect(page.getByText("OpenStreetMap", { exact: true })).toBeVisible();
    expect(await page.locator('[data-slot="button"]').evaluateAll((nodes) => nodes.every((node) => getComputedStyle(node).borderRadius === "12px"))).toBe(true);
    await page.getByText("Your trip, mapped out.").scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`result-${width}.png`) });
  }
  await page.getByRole("tab", { name: /Daily logs/ }).click();
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    await noOverflow();
    await expect(page.getByRole("region", { name: /Scrollable duty graph/ }).first()).toBeVisible();
  }
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".print-only")).toBeVisible();
  await expect(page.locator(".trip-form")).toBeHidden();
  expect(await page.locator(".print-only .duty-trace").evaluateAll((nodes) => nodes.every((node) => getComputedStyle(node).stroke === "rgb(16, 17, 20)"))).toBe(true);
  await page.screenshot({ path: info.outputPath("print-grayscale.png"), fullPage: true });
  const printed = info.outputPath("browser-print.pdf");
  await page.pdf({ path: printed, preferCSSPageSize: true });
  const python = fileURLToPath(new URL("../../backend/.venv/bin/python", import.meta.url));
  expect(execFileSync(python, ["-c", "from pypdf import PdfReader; import sys; print(len(PdfReader(sys.argv[1]).pages))", printed], { encoding: "utf8" }).trim()).toBe("1");
});

test("validation, loading and blocked states fit every target width", async ({ page }, info) => {
  await setupTrip(page, "Boston, MA");
  await page.getByLabel("Current cycle used").fill("71");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByLabel("Current cycle used")).toHaveAttribute("aria-invalid", "true");
  const inspect = async (state: string) => {
    for (const width of [320, 375, 425, 640, 768, 1024, 1280, 1536]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      if (width === 375 || width === 1280) await page.screenshot({ path: info.outputPath(`${state}-${width}.png`), fullPage: true });
    }
  };
  await inspect("validation");
  await page.getByLabel("Current cycle used").fill("0");
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/v1/trips/plan", async (route) => {
    const response = await route.fetch(); await gate; await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(page.getByText("Finding your way forward", { exact: true })).toBeVisible();
  await inspect("loading");
  release();
  await expect(page.getByRole("alert")).toContainText("No feasible sequence");
  await inspect("blocked");
});
