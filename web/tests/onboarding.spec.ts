import { expect, test, type Locator } from "@playwright/test";

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

/**
 * Types a value into a wizard field and waits for it to hold.
 *
 * Each step's save is awaited before the wizard advances, so a spec walking
 * the wizard must wait for the next step to render rather than firing every
 * click at once — clicking blind outruns the save still in flight, which is
 * the impatience the disabled button exists to refuse.
 *
 * These inputs are controlled by React state. A fill that lands before the
 * page is interactive sets the DOM value and is then discarded by the next
 * render, silently leaving the field on whatever was loaded — which for a
 * question the business has answered before is the *previous* answer, not a
 * blank. Retrying until the value sticks makes the spec assert what it came
 * to assert rather than a stale answer that happens to still be there.
 *
 * Args:
 *   field: The input to fill.
 *   value: The answer to type.
 */
async function fillAndConfirm(field: Locator, value: string) {
  await expect(async () => {
    await field.fill(value);
    expect(await field.inputValue()).toBe(value);
  }).toPass({ timeout: 10_000 });
}

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

// Fills its own way to step 2 rather than inheriting a filled step 1, so it
// proves what it asserts whatever ran before it.
test("Back still goes back when the save is failing, and keeps the answer", async ({
  page,
}) => {
  await page.goto("/onboarding");

  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  for (const question of FIRST_STEP_QUESTIONS) {
    await fillAndConfirm(page.getByLabel(question), "Filled to reach step 2");
  }
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByText("Step 2 of 5")).toBeVisible();

  // Typed on the step the failing save will refuse to write. Asserting it is
  // still here after Back is what proves the answers survive the failure —
  // an answer loaded from the engine would prove only that the engine had it
  // all along.
  const strandedAnswer = "Typed while the engine was unreachable";
  const stepTwoField = page.getByRole("textbox").first();
  await fillAndConfirm(stepTwoField, strandedAnswer);

  // Server actions POST to the page's own URL, so aborting those requests is
  // the engine going unreachable as far as the wizard can tell — the same
  // failure as stopping the engine container, without stopping it for the
  // specs running beside this one.
  await page.route("**/onboarding", async (route, request) => {
    if (request.method() === "POST") return route.abort();
    return route.continue();
  });

  await page.getByRole("button", { name: "← Back" }).click();
  await expect(page.getByText("Step 1 of 5")).toBeVisible();

  // Forward still refuses to leave a step whose write did not land, so the
  // return trip needs the saving working again — which is also the recovery
  // the fix promises: the answer held through the failure is written by the
  // next save that succeeds.
  await page.unrouteAll();
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByText("Step 2 of 5")).toBeVisible();
  await expect(stepTwoField).toHaveValue(strandedAnswer);
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
    // `count()` resolves immediately, unlike the locators that auto-wait, so
    // it must not be asked which fields are on screen until the step has
    // actually rendered. Before that it answers "none", the loop fills
    // nothing, and the wizard advances carrying whatever it loaded — which
    // for a question answered on an earlier visit is the previous answer.
    await expect(page.getByText(`Step ${step} of 5`)).toBeVisible();
    for (const [label, value] of Object.entries(answers)) {
      const field = page.getByLabel(label);
      if (await field.count()) await fillAndConfirm(field, value);
    }
    await page.getByRole("button", { name: "Next →" }).click();
    await expect(page.getByText(`Step ${step + 1} of 5`)).toBeVisible();
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
