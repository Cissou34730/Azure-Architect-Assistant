import { defineConfig, devices } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const envPath = path.join(repoRoot, ".env");

const resolveFrontendPort = () => {
  const envPort = Number(process.env.FRONTEND_PORT);
  if (Number.isFinite(envPort) && envPort > 0) {
    return envPort;
  }

  if (fs.existsSync(envPath)) {
    const envText = fs.readFileSync(envPath, "utf8");
    const match = envText.match(/^FRONTEND_PORT\s*=\s*(\d+)/m);
    if (match) {
      const filePort = Number(match[1]);
      if (Number.isFinite(filePort) && filePort > 0) {
        return filePort;
      }
    }
  }

  return 5173;
};

const frontendPort = resolveFrontendPort();
const baseURL = `http://localhost:${frontendPort}`;

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    cwd: __dirname,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
