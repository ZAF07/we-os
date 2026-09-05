import { expect, test } from "@playwright/test";

// These specs share one mutable fixture — a tenant that starts blank and ends
// filled in — so they must run in declaration order, not merely one at a time.
test.describe.configure({ mode: "serial" });

/**
 * The wizard renders entirely from the engine's published question set,
 * so these assert on what the seed set actually asks — including the
 * four fields the old wizard never collected — rather than on any
 * question hardcoded in the frontend.
 *
 * This file runs in its own Playwright project against the *blank* tenant —
 * the business that has answered nothing — because a complete Brand DNA
 * pre-fills every field, leaving the wizard nothing to gate on and no honest
 * way to walk it. The specs below share a mutable fixture — the gating spec
 * needs a blank tenant and the last spec fills it in — so they run serially
 * *in declaration order*, which one worker alone does not guarantee. Blankness
 * is re-established by the seed on every stack start, not by these specs.
 */
const FIRST_STEP_QUESTIONS = [
  "What is your business called?",
  "What do you sell?",
  "What category or industry are you in?",
  "What do your main products or services cost?",
];

const CRAFTED_ARTIFACT_QUESTIONS = [
  "Core value proposition",
  "Primary customer promise",
  "Key differentiators",
  "Brand personality",
  "Tone of voice",
];

test("the wizard renders the published questions, each explaining itself", async ({
  page,
}) => {
  await page.goto("/onboarding");

  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  for (const question of FIRST_STEP_QUESTIONS) {
    await expect(page.getByText(question)).toBeVisible();
  }
  await expect(page.getByText(/^Why we ask:/).first()).toBeVisible();
});

test("onboarding never asks for work the engine owes the business", async ({
  page,
}) => {
  await page.goto("/onboarding");

  for (const label of CRAFTED_ARTIFACT_QUESTIONS) {
    await expect(page.getByText(label, { exact: true })).toHaveCount(0);
  }
});

// Declared before the specs that answer anything, because it needs a tenant
// that has answered nothing and they leave one that has.
test("required-field validation blocks advancing past an incomplete step", async ({
  page,
}) => {
  await page.goto("/onboarding");

  // Step 1 is pre-filled for a tenant that has already answered, so Next
  // succeeds and the refusal this spec exists to prove can never fire. Saying
  // which command re-blanks the tenant beats a bare assertion failure on error
  // text that was never going to render.
  await expect(
    page.getByLabel("What is your business called?"),
    "The blank tenant is not blank — an earlier run filled it in. The seed " +
      "re-blanks it on stack start: run `make e2e-up` (or `make test-e2e`, " +
      "which brings the stack up itself) before re-running this spec.",
  ).toHaveValue("");

  await page.getByRole("button", { name: "Next →" }).click();
  await expect(
    page.getByText("Fill in the required fields to continue."),
  ).toBeVisible();
  await expect(page.getByText("Step 1 of 5")).toBeVisible();
});

test("answers save partway and are still there on return", async ({ page }) => {
  await page.goto("/onboarding");

  await page.getByLabel("What is your business called?").fill("Acme Coffee");
  await page
    .getByLabel("What do you sell?")
    .fill("Specialty coffee kits and subscriptions");
  await page.getByLabel("What category or industry are you in?").fill("Coffee");
  await page
    .getByLabel("What do your main products or services cost?")
    .fill("$18–24 a bag");
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByText("Step 2 of 5")).toBeVisible();

  await page.goto("/onboarding");
  await expect(page.getByLabel("What is your business called?")).toHaveValue(
    "Acme Coffee",
  );
  await expect(page.getByText(/answered so far/)).toBeVisible();
});

// Last, because it completes the Brand DNA and leaves nothing for the gating
// spec above to block on until the seed re-blanks the tenant.
test("completing the questionnaire lands on the Brand screen with the answers", async ({
  page,
}) => {
  await page.goto("/onboarding");

  // Deliberately not the name the partial-save spec above writes. That spec
  // persists "Acme Coffee", so asserting on it here would pass whether or not
  // this spec's own answers landed — the exact tautology this test exists to
  // avoid. A name only this spec writes keeps the Brand assertion honest.
  const businessName = "Peakline Roasters";

  const answers: Record<string, string> = {
    "What is your business called?": businessName,
    "What do you sell?": "Specialty coffee kits and subscriptions",
    "What category or industry are you in?": "Specialty coffee",
    "What do your main products or services cost?": "$18–24 a bag",
    "Who buys from you? Describe each distinct group, most important first.":
      "Urban commuters",
    "What problems do those buyers hire you to solve?":
      "Long queues at cafes before work.",
    "When a customer picks you over an alternative, what decided it?":
      "We ship within a day of roasting.",
    "Where do you serve customers?": "Australia-wide, online only",
    "What languages do your customers speak?": "English",
    "What can you spend on marketing in a typical month?": "$2,000 a month",
    "What must never appear in your marketing?": "No health claims.",
  };

  for (let step = 1; step <= 4; step += 1) {
    for (const [label, value] of Object.entries(answers)) {
      const field = page.getByLabel(label);
      if (await field.count()) await field.fill(value);
    }
    await page.getByRole("button", { name: "Next →" }).click();
  }
  await page.getByRole("button", { name: "Finish onboarding" }).click();

  await expect(page).toHaveURL("/brand");
  // The blank tenant is seeded under a different organization name, so seeing
  // this answer here proves it won over the organization name — the rule in
  // `questionnaire/render.py` that nothing else covers.
  await expect(page.getByText(businessName)).toBeVisible();
  // The answers completed the Brand DNA, so the gate now passes — which is what
  // makes the walk worth testing: the business can reach the pipeline.
  await expect(page.getByText("Every Required answer is in")).toBeVisible();

  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: "Reach & constraints" }).click();
  await expect(page.getByText("Australia-wide, online only")).toBeVisible();
  await expect(page.getByText("$2,000 a month")).toBeVisible();
});
