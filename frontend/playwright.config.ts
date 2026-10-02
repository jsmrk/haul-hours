import { fileURLToPath, URL } from "node:url";
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e", fullyParallel: false, workers: 1, timeout: 30000,
  use: { baseURL: "http://127.0.0.1:5187", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    { command: ".venv/bin/python manage.py runserver 127.0.0.1:8017 --noreload", cwd: fileURLToPath(new URL("../backend", import.meta.url)), url: "http://127.0.0.1:8017/api/v1/health", reuseExistingServer: false,
      env: { DJANGO_DEBUG: "true", PROVIDER_MODE: "fixtures", FRONTEND_ORIGINS: "http://127.0.0.1:5187", DJANGO_ALLOWED_HOSTS: "127.0.0.1,localhost" } },
    { command: "npm run dev -- --port 5187 --strictPort", url: "http://127.0.0.1:5187", reuseExistingServer: false,
      env: { VITE_API_BASE_URL: "http://127.0.0.1:8017" } },
  ],
});
