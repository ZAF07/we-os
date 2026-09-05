import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    // The browser suite runs against a long-lived test tenant whose campaigns
    // outlive the run that created them, so a campaign name reused across runs
    // matches two rows and a `getByText` becomes a strict-mode violation the
    // second time. `uniqueName` in tests/fixtures.ts mints unique text.
    //
    // Every spec already did this with an inline `Date.now()`, which worked and
    // was a convention held in one author's head — the next spec written
    // against a freshly-seeded tenant would pass, and start failing for someone
    // else a week later. This makes the linter hold it instead.
    files: ["tests/**/*.ts"],
    ignores: ["tests/fixtures.ts"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "CallExpression[callee.object.name='Date'][callee.property.name='now']",
          message:
            "Do not mint test data with Date.now() inline. Use uniqueName() " +
            "from tests/fixtures.ts, so the uniqueness the shared tenant needs " +
            "has one home rather than a copy per spec.",
        },
      ],
    },
  },
]);

export default eslintConfig;
