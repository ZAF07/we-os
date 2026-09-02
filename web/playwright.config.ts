import path from "node:path";

import { defineConfig, devices } from "@playwright/test";
import dotenv from "dotenv";

// Mirror Next.js's own resolution so the tests and the app read the same
// config: `.env.local` wins, `.env` fills the rest. dotenv does not overwrite
// an already-set variable, so loading `.env.local` first gives it precedence.
for (const file of [".env.local", ".env"]) {
  dotenv.config({ path: path.join(__dirname, file) });
}

const PORT = 3100;
const STORAGE_STATE = path.join(__dirname, ".auth/user.json");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  // The `setup` project signs in once; `chromium` reuses the saved session,
  // since clerkMiddleware protects every application route.
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
  ],
  webServer: {
    command: `pnpm dev --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
