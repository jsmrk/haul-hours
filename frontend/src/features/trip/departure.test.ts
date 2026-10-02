import { describe, expect, it } from "vitest";
import { localTimeForInstant, resolveDeparture } from "./departure";

describe("home-terminal departure", () => {
  it("rejects nonexistent times even with an explicit fold choice", () => {
    expect(() => resolveDeparture("2026-03-08T02:30", "America/New_York")).toThrow(/does not exist/);
    expect(() => resolveDeparture("2026-03-08T02:30", "America/New_York", "later")).toThrow(/does not exist/);
  });
  it("requires a choice for repeated times and preserves its UTC instant", () => {
    expect(() => resolveDeparture("2026-11-01T01:30", "America/New_York")).toThrow(/occurs twice/);
    expect(resolveDeparture("2026-11-01T01:30", "America/New_York", "earlier")).toBe("2026-11-01T05:30:00Z");
    expect(resolveDeparture("2026-11-01T01:30", "America/New_York", "later")).toBe("2026-11-01T06:30:00Z");
  });
  it("changes a default wall-time display without changing the underlying instant", () => {
    expect(localTimeForInstant("2026-10-02T12:00:00Z", "America/New_York")).toBe("2026-10-02T08:00");
    expect(localTimeForInstant("2026-10-02T12:00:00Z", "America/Chicago")).toBe("2026-10-02T07:00");
    expect(resolveDeparture("2026-10-02T08:00", "America/New_York")).toBe("2026-10-02T12:00:00Z");
  });
});
