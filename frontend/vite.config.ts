import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ command, mode }) => {
  if (command === "build" && process.env["VERCEL"]) {
    const environment = loadEnv(mode, fileURLToPath(new URL("./", import.meta.url)), "VITE_");
    const configured = process.env["VITE_API_BASE_URL"] ?? environment["VITE_API_BASE_URL"] ?? "";
    let valid = false;
    try {
      const url = new URL(configured);
      valid = url.protocol === "https:" && Boolean(url.hostname) && !url.username && !url.password && !url.search && !url.hash;
    } catch { /* The error below explains the required production setting. */ }
    if (!valid) throw new Error("Set VITE_API_BASE_URL to the HTTPS backend origin before deploying the frontend.");
  }
  return {
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  optimizeDeps: { include: ["leaflet", "react-leaflet"] },
  server: { port: Number(process.env["HAUL_HOURS_WEB_PORT"] ?? 5173), proxy: { "/api": `http://127.0.0.1:${process.env["HAUL_HOURS_API_PORT"] ?? "8000"}` } },
  };
});
