import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/** Local npm run dev → 127.0.0.1. Docker Compose → http://backend:8000 (see docker-compose.yml). */
function apiProxyTarget(mode: string) {
  const env = loadEnv(mode, process.cwd(), "");
  return (env.VITE_PROXY_TARGET || process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8000").replace(
    /\/+$/,
    "",
  );
}

function proxyConfig(target: string) {
  return {
    "/api": {
      target,
      changeOrigin: true,
      timeout: 120000,
      proxyTimeout: 120000,
    },
    "/status": {
      target,
      changeOrigin: true,
      timeout: 30000,
    },
  };
}

export default defineConfig(({ mode }) => {
  const target = apiProxyTarget(mode);
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: proxyConfig(target),
    },
    preview: {
      port: 4173,
      proxy: proxyConfig(target),
    },
  };
});
