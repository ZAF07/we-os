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
const BLANK_STORAGE_STATE = path.join(__dirname, ".auth/blank-user.json");
const TENANTLESS_STORAGE_STATE = path.join(
  __dirname,
  ".auth/tenantless-user.json",
);

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
  // The `setup` project signs both test users in; the two signed-in projects
  // reuse the saved sessions, since clerkMiddleware protects every route in the
  // app half.
  //
  // Two signed-in projects because the suite needs two tenants. `chromium` runs
  // against the seeded business, whose Brand DNA is complete so campaigns can
  // be created. `chromium-onboarding` runs the wizard's specs against the blank
  // business, which has answered nothing — and runs them with one worker,
  // because they share a mutable fixture: the first reads a blank tenant and
  // the second fills it in. `testIgnore` on `chromium` keeps the onboarding
  // and public files from running twice.
  //
  // `chromium-public` is the visitor: no saved session and no dependency on
  // `setup`, because the public half must work with neither. A change that
  // accidentally puts the Landing behind auth fails here rather than passing
  // on a signed-in cookie.
  //
  // `chromium-tenantless` is a person who has just signed up: a session that
  // carries no organization. It proves the gate — that such a session cannot
  // reach the app half — and walks the welcome flow that creates the
  // business. One worker, because its specs share a mutable fixture: the user
  // stops being tenantless the moment a spec names a business, and each spec
  // deletes what it created so the next one starts tenantless again. Its
  // sign-in is a setup project of its own, so a missing tenantless user fails
  // this project alone rather than every signed-in spec.
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    { name: "setup-tenantless", testMatch: /tenantless\.setup\.ts/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["setup"],
      testIgnore: [
        /auth\.setup\.ts/,
        /onboarding\.spec\.ts/,
        /public\.spec\.ts/,
        /tenantless\.(setup|spec)\.ts/,
      ],
    },
    {
      name: "chromium-onboarding",
      use: { ...devices["Desktop Chrome"], storageState: BLANK_STORAGE_STATE },
      dependencies: ["setup"],
      testMatch: /onboarding\.spec\.ts/,
      fullyParallel: false,
      workers: 1,
    },
    {
      name: "chromium-public",
      use: { ...devices["Desktop Chrome"] },
      testMatch: /public\.spec\.ts/,
    },
    {
      name: "chromium-tenantless",
      use: {
        ...devices["Desktop Chrome"],
        storageState: TENANTLESS_STORAGE_STATE,
      },
      dependencies: ["setup-tenantless"],
      testMatch: /tenantless\.spec\.ts/,
      fullyParallel: false,
      workers: 1,
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
