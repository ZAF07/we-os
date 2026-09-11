/**
 * Shared fixtures for the browser suite, and the one convention it must keep.
 *
 * The suite runs against a long-lived test tenant. The seed purges its
 * campaigns on every stack start, so a run against a freshly started stack sees
 * a clean list — but a *second* run against the same stack does not, because
 * every spec that creates a campaign leaves it behind.
 *
 * That makes the text a spec asserts on the sharp edge. A campaign name a
 * previous run also used matches two rows, and a `getByText` that resolved
 * uniquely the first time becomes a strict-mode violation the second. Minting
 * the text here is what stops it: a name from `uniqueName` belongs to the run
 * that created it, so asserting on it is safe however long the tenant lives.
 *
 * `eslint.config.mjs` refuses a `Date.now()` written inline in a spec, so the
 * convention has one home rather than a copy per spec and a note in someone's
 * head.
 */

import { expect, type Page } from "@playwright/test";

let sequence = 0;

/**
 * Returns text unique to this run, for a spec that must assert on what it wrote.
 *
 * The timestamp separates runs; the counter separates values minted inside the
 * same millisecond, which one worker can easily do.
 *
 * Args:
 *   label: What the value is for, so a failure names something readable.
 *
 * Returns:
 *   The label followed by a run-unique suffix.
 */
export function uniqueName(label: string): string {
  sequence += 1;
  return `${label} ${Date.now()}-${sequence}`;
}

/**
 * Creates a campaign through the wizard and lands on its Workspace.
 *
 * The same walk every campaign spec makes; a spec asserting on what happens
 * to a campaign should start here rather than re-typing the wizard.
 *
 * Args:
 *   page: The Playwright page.
 *   name: The campaign name, which must be unique per run.
 *
 * Returns:
 *   The slug the engine gave the campaign, read from the Workspace URL.
 */
export async function createCampaign(
  page: Page,
  name: string,
): Promise<string> {
  await page.goto("/campaigns/new");
  await page.getByLabel("Campaign name").fill(name);
  await page.getByLabel("Primary business objective").fill("An objective");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByLabel("Business KPI").fill("A business target");
  await page.getByLabel("Marketing KPI").fill("A marketing target");
  await page.getByLabel("Creative KPI").fill("A creative target");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("radio").first().click();
  await page.getByLabel("Campaign budget").fill("1000");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("End date").fill("2026-10-27");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("button", { name: "Create campaign" }).click();
  await expect(page.getByRole("navigation", { name: "Stages" })).toBeVisible();
  return new URL(page.url()).pathname.split("/campaigns/")[1];
}
