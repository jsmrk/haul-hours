// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
import config from "../vite.config";

afterEach(() => vi.unstubAllEnvs());

it("refuses a hosted production build without an HTTPS API URL", () => {
  vi.stubEnv("VERCEL", "1");
  for (const value of ["", "http://api.example.test", "https://"]) {
    vi.stubEnv("VITE_API_BASE_URL", value);
    expect(() => {
      if (typeof config === "function") return config({ command: "build", mode: "production" });
      throw new Error("Expected configurable Vite build");
    }).toThrow(/VITE_API_BASE_URL/);
  }
});

it("accepts a hosted production build with a configured HTTPS API URL", () => {
  vi.stubEnv("VERCEL", "1");
  vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
  expect(() => {
    if (typeof config === "function") return config({ command: "build", mode: "production" });
    throw new Error("Expected configurable Vite build");
  }).not.toThrow();
});
