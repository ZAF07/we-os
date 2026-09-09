import path from "node:path";

import { defineConfig } from "vitest/config";

/**
 * Unit tests for the pure logic the screens are built on.
 *
 * Kept separate from the Playwright suite under `tests/`, which drives a real
 * browser against a real engine. This one runs on a clean checkout with no
 * credentials and no server, so the projections between engine vocabulary and
 * operator vocabulary stay covered whatever the end-to-end suite can reach.
 *
 * A jsdom environment so a component that renders a document — the markdown of
 * a deliverable — can be asserted on as elements rather than as source text.
 */
export default defineConfig({
  resolve: {
    alias: { "@": path.join(import.meta.dirname, "src") },
  },
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "jsdom",
  },
});
