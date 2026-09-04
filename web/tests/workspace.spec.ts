import { expect, test } from "@playwright/test";

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
  const name = `Workspace ${Date.now()}`;
  await createCampaign(page, name);

  await expect(page.getByText(name)).toBeVisible();

  for (const phase of ["Research", "Strategy", "Plan", "Produce"]) {
    await expect(
      page.getByRole("button", { name: new RegExp(`^${phase}$`) }),
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
  const name = `No keys ${Date.now()}`;
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
  const name = `Lifecycle ${Date.now()}`;
  await createCampaign(page, name);

  await expect(page.getByText("Draft", { exact: true })).toBeVisible();

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  await expect(
    stageNav.getByRole("button", { name: "Research findings" }),
  ).toContainText("Not started");
});

test("a stage that has produced nothing says so honestly", async ({ page }) => {
  const name = `Empty ${Date.now()}`;
  await createCampaign(page, name);

  const stageNav = page.getByRole("navigation", { name: "Stages" });
  await stageNav.getByRole("button", { name: "Asset prompts" }).click();

  await expect(page.getByText("Nothing produced yet")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Asset prompts" }),
  ).toBeVisible();
});

test("a draft campaign offers to start a run", async ({ page }) => {
  const name = `Runnable ${Date.now()}`;
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
 * The approve and revise paths.
 *
 * These drive a campaign to a live Approval Gate, which needs the engine to
 * actually execute a run — several model calls per stage. They are skipped
 * until the suite can bring up an engine with a seeded tenant, which is issue
 * 13's work; the same behaviour is pinned meanwhile at the engine boundary in
 * `agent-harness/tests/test_workspace_contract.py`, which does run.
 *
 * They are written out rather than left as a TODO so that closing issue 13 is
 * a matter of removing the skip, not of writing the specs from scratch.
 */
test.describe("approval gate", () => {
  test.skip(
    true,
    "Needs an engine with a seeded tenant and a run that reaches a gate — issue 13.",
  );

  test("approving a stage resumes the run into the next one", async ({
    page,
  }) => {
    const name = `Approve ${Date.now()}`;
    await createCampaign(page, name);

    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByRole("button", { name: "Approve" })).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.getByLabel("Deliverable")).not.toBeEmpty();

    await page.getByRole("button", { name: "Approve" }).click();

    await expect(page.getByText(/approved$/)).toBeVisible({ timeout: 120_000 });
    const stageNav = page.getByRole("navigation", { name: "Stages" });
    await expect(
      stageNav.getByRole("button", { name: "Brand strategy" }),
    ).toContainText("Approved");
  });

  test("requesting changes produces a second version carrying the feedback", async ({
    page,
  }) => {
    const name = `Revise ${Date.now()}`;
    await createCampaign(page, name);

    await page.getByRole("button", { name: "Start run" }).click();
    await expect(
      page.getByRole("button", { name: "Request changes" }),
    ).toBeVisible({ timeout: 120_000 });

    await page.getByRole("button", { name: "Request changes" }).click();
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
