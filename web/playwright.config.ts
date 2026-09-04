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

// The e2e compose stack serves the app on the same port, so when it is up
// Playwright must attach rather than start a second server of its own. Anything
// else double-binds the port and the suite fails for a reason that has nothing
// to do with the code.
const STACK_IS_UP = process.env.E2E_STACK === "compose";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  // A spec that starts a run waits on the engine walking real pipeline stages,
  // and the dev server compiles a route the first time it is hit. Neither fits
  // in the 30s default under parallel load, and a timeout there looks like a
  // product failure when it is only a slow first paint.
  timeout: 120_000,
  // The whole suite drives one Next dev server, which compiles routes on demand
  // and is the bottleneck long before the browser is. Five workers saturate it
  // and specs then fail on a slow first paint rather than on anything real;
  // two keeps it responsive and the suite still finishes in about a minute.
  workers: 2,
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
  webServer: STACK_IS_UP
    ? undefined
    : {
        command: `pnpm dev --port ${PORT}`,
        url: `http://localhost:${PORT}`,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
