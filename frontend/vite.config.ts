import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + "/../", "");

  const frontendPort = parseInt(env.FRONTEND_PORT || "5173");
  const backendPort = env.BACKEND_PORT;
  const apiBaseUrl =
    env.BACKEND_URL ||
    (backendPort ? `http://localhost:${backendPort}` : "http://localhost:8000");

  return {
    plugins: [react()],
    envDir: "../",
    server: {
      port: frontendPort,
    },
    define: {
      "import.meta.env.BACKEND_URL": JSON.stringify(apiBaseUrl),
    },
    build: {
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          manualChunks: {
            "react-vendor": ["react", "react-dom"],
            "router-vendor": ["react-router-dom"],
            "mermaid-vendor": ["mermaid"],
          },
        },
      },
    },
  };
});
