import { defineConfig, devices } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const dirName = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(dirName, "..");
const envPath = path.join(repoRoot, ".env");

const resolveFrontendPort = () => {
  const envPort = Number(process.env.FRONTEND_PORT);
  if (Number.isFinite(envPort) && envPort > 0) {
    return envPort;
  }

  if (fs.existsSync(envPath)) {
    const envText = fs.readFileSync(envPath, "utf8");
    const match = /^FRONTEND_PORT\s*=\s*(\d+)/m.exec(envText);
    if (match !== null) {
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
const isCi = typeof process.env.CI === "string" && process.env.CI !== "";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  retries: isCi ? 2 : 0,
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: baseURL,
    reuseExistingServer: !isCi,
    cwd: dirName,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
