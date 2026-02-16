import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + "/../", "");
  const frontendPortRaw = env.FRONTEND_PORT?.trim();
  if (frontendPortRaw === undefined || frontendPortRaw === "") {
    throw new Error("FRONTEND_PORT is required in .env");
  }
  const frontendPort = Number.parseInt(frontendPortRaw, 10);
  if (Number.isNaN(frontendPort)) {
    throw new Error("FRONTEND_PORT must be a valid integer");
  }

  const backendUrl = env.BACKEND_URL?.trim();
  if (backendUrl === undefined || backendUrl === "") {
    throw new Error("BACKEND_URL is required in .env");
  }
  const apiBasePath = env.VITE_API_BASE?.trim();
  if (apiBasePath === undefined || apiBasePath === "") {
    throw new Error("VITE_API_BASE is required in .env");
  }
  if (!apiBasePath.startsWith("/")) {
    throw new Error("VITE_API_BASE must start with '/' (example: /api)");
  }

  return {
    plugins: [react()],
    envDir: "../",
    server: {
      port: frontendPort,
      proxy: {
        [apiBasePath]: {
          target: backendUrl,
          changeOrigin: true,
        },
      },
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
