import { expect, test } from "@playwright/test";

import { createCampaign, uniqueName } from "./fixtures";

/**
 * A specialist that lacks a fact only the business knows asks for it and the
 * run halts (ADR-0028). The e2e engine runs the scripted provider with its
 * performance-plan specialist in ask mode (`MARKETING_OS_SCRIPTED_ASK_STAGE`),
 * so a run approved through its first two gates halts on a fixed question,
 * identically every time, with no model called.
 *
 * What is under test is what the owner sees: the Workspace says the stage has
 * a question, Home lists the campaign as a red Decision, following it shows
 * the question and the reason the specialist gave, and answering it sends the
 * run on to its next gate on its own. One test rather than two, because the
 * answer joins the tenant's Brand DNA and the scripted specialist then asks
 * nothing — so only the first walk on a fresh stack ever sees the question.
 */

test("a specialist's question halts the run, reaches Home, and answering resumes it", async ({
  page,
}) => {
  // Before any specialist has asked, the Brand page's Clarifications tab says
  // so, and says where its entries will come from.
  await page.goto("/brand");
  const index = page.getByRole("navigation", { name: "Brand sections" });
  await index.getByRole("button", { name: /Clarifications/ }).click();
  await expect(
    page.getByRole("heading", { name: "Clarifications" }),
  ).toBeVisible();
  await expect(page.getByText(/No Clarifications yet/)).toBeVisible();

  const slug = await createCampaign(page, uniqueName("Clarify"));

  // Two approvals take the run to the performance plan, whose specialist asks.
  await page.getByRole("button", { name: "Start run" }).click();
  const approve = page.getByRole("button", { name: "Approve", exact: true });
  await expect(approve).toBeVisible({ timeout: 120_000 });
  await expect(
    page.getByText("Approving starts Campaign strategy."),
  ).toBeVisible();
  await approve.click();
  await expect(
    page.getByText("Approving starts Performance plan."),
  ).toBeVisible({
    timeout: 120_000,
  });
  await approve.click();

  // The Workspace follows the run to the stage that asked, and says so: the
  // decision rail names the stage (exact, since the progress rail narrates the
  // same sentence with a full stop) and offers no approval.
  await expect(
    page.getByText("Performance plan has a question for you", { exact: true }),
  ).toBeVisible({ timeout: 120_000 });
  await expect(page.getByRole("log", { name: "Run progress" })).toContainText(
    "Waiting for your answer",
  );
  await expect(
    page.getByRole("button", { name: "Approve", exact: true }),
  ).toHaveCount(0);

  // Home derives the queue from real campaign state, so the halted campaign is
  // on it — tagged Decision in red, and leading to the questions.
  await page.goto("/home");
  const queue = page.getByRole("list", { name: "Decision queue" });
  const href = `/campaigns/${slug}/clarifications`;
  const link = queue.locator(`a[href="${href}"]`);
  await expect(link).toBeVisible();
  const row = queue
    .locator("li")
    .filter({ has: page.locator(`a[href="${href}"]`) });
  await expect(row).toContainText("Plan has a question for you.");
  await expect(row.getByText("Decision", { exact: true })).toHaveClass(
    /text-red-700/,
  );

  await link.click();
  await expect(
    page.getByRole("heading", { name: "Questions for you" }),
  ).toBeVisible();
  const questions = page.getByRole("list", { name: "Questions" });
  await expect(questions).toContainText("email list");
  await expect(questions).toContainText("Why we ask:");
  await expect(questions).toContainText("build one");

  // Answering resumes the run: the plan re-runs from a Brand DNA that now
  // carries the answer, and the Workspace follows it to its own gate.
  const send = page.getByRole("button", { name: "Send answers" });
  await expect(send).toBeDisabled();
  await page
    .getByLabel(/email list/)
    .fill("Yes, about 1,200 subscribers who opted in at the front desk.");
  await send.click();
  await expect(page).toHaveURL(new RegExp(`/campaigns/${slug}$`));
  await expect(page.getByText("Approving starts Creative brief.")).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.getByRole("log", { name: "Run progress" })).toContainText(
    "You answered.",
  );

  // Home no longer leads to the questions: the campaign is waiting for an
  // approval now, which is a different Decision.
  await page.goto("/home");
  await expect(queue.locator(`a[href="${href}"]`)).toHaveCount(0);
  await expect(queue.locator(`a[href="/campaigns/${slug}"]`)).toBeVisible();

  // The answer is Brand DNA now: the Brand page lists it under Clarifications
  // with the question, the reason, and which stage of which campaign asked —
  // and it can be corrected there. The correction re-runs nothing: the
  // campaign is still at the gate it reached.
  await page.goto("/brand");
  await index.getByRole("button", { name: /Clarifications/ }).click();
  const list = page.getByRole("list", { name: "Clarifications" });
  await expect(list).toContainText("email list");
  await expect(list).toContainText("Why it was asked:");
  await expect(list).toContainText(
    `Asked by Performance plan for campaign ${slug}`,
  );
  await expect(list).toContainText(
    "Yes, about 1,200 subscribers who opted in at the front desk.",
  );

  await page
    .getByRole("button", { name: /^Edit answer: .*email list/ })
    .click();
  const corrected = uniqueName("About 1,300 now");
  await page.getByLabel(/email list/).fill(corrected);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(list).toContainText(corrected, { timeout: 30_000 });
  await expect(
    page.getByRole("button", { name: "Save", exact: true }),
  ).toHaveCount(0);

  await page.reload();
  await index.getByRole("button", { name: /Clarifications/ }).click();
  await expect(list).toContainText(corrected);

  await page.goto(`/campaigns/${slug}`);
  await expect(page.getByText("Approving starts Creative brief.")).toBeVisible({
    timeout: 30_000,
  });
});
