import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** Browser calls stay on the Vite origin; these forward /api → FastAPI (default port 8000). */
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

/** Long PDF + Gemini + retries can exceed default proxy/socket timeouts → ERR_CONNECTION_RESET. */
const API_PROXY_TIMEOUT_MS = Number(process.env.VITE_API_PROXY_TIMEOUT_MS ?? 600_000);

const apiProxy = {
  "/api": {
    target: API_PROXY_TARGET,
    changeOrigin: true,
    timeout: API_PROXY_TIMEOUT_MS,
    proxyTimeout: API_PROXY_TIMEOUT_MS,
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
});
