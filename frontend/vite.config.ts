import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  optimizeDeps: { include: ["leaflet", "react-leaflet"] },
  server: { port: Number(process.env["HAUL_HOURS_WEB_PORT"] ?? 5173), proxy: { "/api": `http://127.0.0.1:${process.env["HAUL_HOURS_API_PORT"] ?? "8000"}` } },
});
