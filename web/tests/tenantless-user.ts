/**
 * The tenantless test user: who it is, and why its project may be skipped.
 *
 * Shared by the tenantless sign-in and its specs, which may not import each
 * other — Playwright refuses a test file that imports another test file.
 */

export const TENANTLESS_EMAIL = process.env.E2E_CLERK_TENANTLESS_USER_EMAIL;

export const TENANTLESS_SKIP_REASON =
  "Set E2E_CLERK_TENANTLESS_USER_EMAIL to a Clerk test user that belongs " +
  "to no organization, in web/.env.local. See web/.env.local.example.";
