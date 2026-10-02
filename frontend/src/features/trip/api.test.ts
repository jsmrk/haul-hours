import { afterEach, expect, it, vi } from "vitest";
import shortFixture from "@/test/fixtures/short-plan.json";
import { ApiProblem, downloadLogs, planTrip, searchLocations } from "./api";
import { parsePlanResult } from "./validation";

const result = parsePlanResult(shortFixture);
const closeBodies: (() => void)[] = [];

// A transport double that returns headers immediately and keeps its body pending,
// as fetch does when a connection stalls after receiving response headers.
function stallBody(contentType = "application/json") {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, options) => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        const abort = () => controller.error(new DOMException("Cancelled", "AbortError"));
        options?.signal?.addEventListener("abort", abort, { once: true });
        closeBodies.push(() => {
          options?.signal?.removeEventListener("abort", abort);
          if (!options?.signal?.aborted) controller.close();
        });
      },
    });
    return new Response(body, { headers: { "Content-Type": contentType } });
  });
}

afterEach(() => {
  closeBodies.splice(0).forEach((close) => close());
  vi.useRealTimers();
});

it("cancels a location search while its response body is still downloading", async () => {
  stallBody();
  const controller = new AbortController();
  let failure: unknown;
  const pending = searchLocations("Pittsburgh", controller.signal).catch((error: unknown) => { failure = error; });
  await Promise.resolve();
  controller.abort();
  await vi.waitFor(() => expect(failure).toBeInstanceOf(DOMException));
  expect(failure).toHaveProperty("name", "AbortError");
  await pending;
});

it.each([
  { name: "location search", timeout: 26000, run: () => searchLocations("Pittsburgh", new AbortController().signal) },
  { name: "trip planning", timeout: 190000, run: () => planTrip(result.request, new AbortController().signal) },
  { name: "PDF export", timeout: 30000, run: () => downloadLogs(result, {}), contentType: "application/pdf" },
])("times out $name when headers arrive but the body stalls", async ({ run, timeout, contentType }) => {
  vi.useFakeTimers();
  stallBody(contentType);
  let failure: unknown;
  const pending = run().catch((error: unknown) => { failure = error; });
  await vi.advanceTimersByTimeAsync(timeout);
  expect(failure).toBeInstanceOf(ApiProblem);
  expect(failure).toHaveProperty("code", "CLIENT_TIMEOUT");
  expect(failure).toHaveProperty("retryable", true);
  await pending;
});

it("reports malformed JSON as an invalid response instead of a connection failure", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{broken-json"));
  await expect(searchLocations("Pittsburgh", new AbortController().signal)).rejects.toHaveProperty("code", "INVALID_RESPONSE");
});
