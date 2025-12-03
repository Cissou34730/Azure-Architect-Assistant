import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + "/../", "");

  const frontendPort = parseInt(env.FRONTEND_PORT || "5173");
  const apiBaseUrl = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      proxy: {
        "/api": {
          target: apiBaseUrl,
          changeOrigin: true,
        },
      },
    },
    define: {
      "import.meta.env.VITE_API_BASE_URL": JSON.stringify(apiBaseUrl),
    },
  };
});
