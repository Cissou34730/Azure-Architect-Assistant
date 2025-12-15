import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + "/../", "");

  const frontendPort = parseInt(env.FRONTEND_PORT || "5173");
  const apiBaseUrl = env.BACKEND_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    envDir: "../",
    server: {
      port: frontendPort,
    },
    define: {
      "import.meta.env.BACKEND_URL": JSON.stringify(apiBaseUrl),
    },
  };
});
