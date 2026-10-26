import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the browser talks to Vite (port 5173); requests starting with
// /api are forwarded to the Python backend so we don't need CORS or extra config.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
