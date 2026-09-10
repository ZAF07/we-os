import { expect, test } from "@playwright/test";

import { uniqueName } from "./fixtures";

/**
 * The Workspace renders the tenant's real campaign, so these specs create one
 * and assert on what the engine actually reports — the operator Phases, the
 * per-stage list, and the decision the campaign is asking for. There are no
 * fixture campaigns left to assert against.
 *
 * Every assertion here checks rendered content, never only a URL. Slice 10
 * showed why: a spec asserting `toHaveURL(...)` alone stayed green over a
 * workspace route that answered "Campaign not found" for every real campaign.
 */

/**
 * Creates a campaign through the wizard and lands on its Workspace.
 *
 * Args:
 *   page: The Playwright page.
 *   name: The campaign name, which must be unique per run.
 */
async function createCampaign(
  page: import("@playwright/test").Page,
  name: string,
): Promise<void> {
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
}

test("a new campaign's Workspace renders its Phases and stages", async ({
  page,
}) => {
  const name = uniqueName("Workspace");
  await createCampaign(page, name);

  await expect(page.getByText(name)).toBeVisible();

  // The stepper numbers each Phase, so its accessible name is "1 Research".
  const phases = ["Research", "Strategy", "Plan", "Produce"];
  for (const [index, phase] of phases.entries()) {
    await expect(
      page.getByRole("button", { name: `${index + 1} ${phase}` }),
    ).toBeVisible();
  }

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  for (const stage of [
    "Research findings",
    "Brand strategy",
    "Campaign strategy",
    "Performance plan",
    "Creative brief",
    "Asset prompts",
  ]) {
    await expect(stageNav.getByRole("button", { name: stage })).toBeVisible();
  }
});

test("the stepper shows no raw engine stage keys", async ({ page }) => {
  const name = uniqueName("No keys");
  await createCampaign(page, name);

  for (const key of [
    "brand-strategy",
    "campaign-strategy",
    "performance-plan",
    "creative-brief",
    "asset-prompts",
  ]) {
    await expect(page.getByText(key, { exact: true })).toHaveCount(0);
  }
});

test("lifecycle status renders separately from stage progress", async ({
  page,
}) => {
  const name = uniqueName("Lifecycle");
  await createCampaign(page, name);

  await expect(page.getByText("Draft", { exact: true })).toBeVisible();

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  await expect(
    stageNav.getByRole("button", { name: "Research findings" }),
  ).toContainText("Not started");
});

test("a stage that has produced nothing says so honestly", async ({ page }) => {
  const name = uniqueName("Empty");
  await createCampaign(page, name);

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  await stageNav.getByRole("button", { name: "Asset prompts" }).click();

  await expect(page.getByText("Nothing produced yet")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Asset prompts" }),
  ).toBeVisible();
});

test("a draft campaign offers to start a run", async ({ page }) => {
  const name = uniqueName("Runnable");
  await createCampaign(page, name);

  await expect(page.getByText("Nothing running")).toBeVisible();
  await expect(page.getByRole("button", { name: "Start run" })).toBeVisible();
});

test("an unknown campaign slug renders not found, not a broken page", async ({
  page,
}) => {
  await page.goto("/campaigns/no-such-campaign-anywhere");

  await expect(
    page.getByRole("heading", { name: "Campaign not found" }),
  ).toBeVisible();
});

/**
 * The approve and revise paths — the decision the whole product exists for.
 *
 * These drive a campaign to a live Approval Gate. The e2e stack runs the engine
 * on the scripted provider, so a run reaches that gate in seconds, identically
 * every time, without calling a model: what is under test is the interface, not
 * anyone's prose.
 */
test.describe("approval gate", () => {
  test("approving a stage resumes the run into the next one", async ({
    page,
  }) => {
    const name = uniqueName("Approve");
    await createCampaign(page, name);

    await page.getByRole("button", { name: "Start run" }).click();

    // The run halts at the brand-strategy gate, and the Workspace follows it
    // there rather than leaving the person on the stage that was current when
    // the page loaded.
    const approve = page.getByRole("button", { name: "Approve", exact: true });
    await expect(approve).toBeVisible({ timeout: 120_000 });
    // Two headings read "Brand strategy" once the deliverable renders: the
    // stage panel's, and the document's own title. `level` tells them apart —
    // the panel heads the stage at h2, and DeliverableContent maps the
    // document's leading `#` to h1.
    await expect(
      page.getByRole("heading", { level: 2, name: "Brand strategy" }),
    ).toBeVisible();
    await expect(page.getByLabel("Deliverable")).not.toBeEmpty();

    // The decision names what it starts before it is made, and the rail says
    // the run is waiting rather than calling a halt a finish.
    await expect(
      page.getByText("Approving starts Campaign strategy."),
    ).toBeVisible();
    await expect(page.getByRole("log", { name: "Run progress" })).toContainText(
      "Waiting for your decision",
    );

    await approve.click();

    // The moment the approval is accepted, the Stages list says which stage
    // the run moved on to — it is never left reading "Not started" — and the
    // rail keeps its feed and returns to Working rather than going blank.
    const stageNav = page.getByRole("navigation", { name: "Stages" });
    const campaignStrategy = stageNav.getByRole("button", {
      name: /^Campaign strategy/,
    });
    await expect(campaignStrategy).not.toContainText("Not started");
    await expect(
      stageNav.getByRole("button", { name: /^Brand strategy/ }),
    ).toContainText("Approved", { timeout: 120_000 });

    // The stream reads through the gate the run left, so the rail narrates
    // the resumed run rather than stopping at the halt it replayed.
    const log = page.getByRole("log", { name: "Run progress" });
    await expect(log).toContainText("You approved Brand strategy.", {
      timeout: 120_000,
    });

    // Campaign strategy is gated too: the run halts there next, and the
    // Workspace follows it to the new decision.
    await expect(campaignStrategy).toContainText("Ready for review", {
      timeout: 120_000,
    });
    await expect(campaignStrategy).toHaveAttribute("aria-current", "step");
    await expect(
      page.getByText("Approving starts Performance plan."),
    ).toBeVisible();
  });

  test("requesting changes produces a second version carrying the feedback", async ({
    page,
  }) => {
    const name = uniqueName("Revise");
    await createCampaign(page, name);

    await page.getByRole("button", { name: "Start run" }).click();
    const requestChanges = page.getByRole("button", {
      name: "Request changes",
    });
    await expect(requestChanges).toBeVisible({ timeout: 120_000 });

    await requestChanges.click();
    await page
      .getByLabel("What do you want changed?")
      .fill("Too premium; we are mid-market.");
    await page.getByRole("button", { name: "Send back" }).click();

    const history = page.getByRole("region", { name: "Version history" });
    await expect(history.getByText("v2")).toBeVisible({ timeout: 120_000 });
    await expect(
      history.getByText("You asked: Too premium; we are mid-market."),
    ).toBeVisible();

    await history.getByRole("button", { name: /^v1/ }).click();
    await expect(page.getByText("Showing v1 of 2")).toBeVisible();
  });
});
