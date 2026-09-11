import { describe, expect, it } from "vitest";

import type { CampaignSummary } from "@/lib/engine";
import { blockedReason, toCampaignRow } from "@/lib/campaigns";

/**
 * Builds a campaign summary as the engine reports one.
 *
 * Args:
 *   overrides: The fields this campaign differs from a fresh draft in.
 *
 * Returns:
 *   The summary.
 */
function campaign(overrides: Partial<CampaignSummary> = {}): CampaignSummary {
  return {
    id: "c",
    name: "c",
    objective: "An objective",
    status: "draft",
    stage_progress: { completed: 0, total: 6, current_stage_key: "research" },
    blocked_stage_key: null,
    ...overrides,
  };
}

describe("blockedReason", () => {
  it("names the holding stage by its title, whatever phase it is in", () => {
    const waiting = campaign({
      status: "awaiting_approval",
      blocked_stage_key: "creative-brief",
    });
    const asking = campaign({
      status: "awaiting_clarification",
      blocked_stage_key: "asset-prompts",
    });
    const stale = campaign({
      status: "running",
      blocked_stage_key: "brand-strategy",
    });

    expect(blockedReason(waiting)).toBe(
      "Creative brief is waiting for your approval.",
    );
    expect(blockedReason(asking)).toBe("Asset prompts has a question for you.");
    expect(blockedReason(stale)).toBe(
      "Brand strategy rests on a decision you have since re-opened.",
    );
  });

  it("still says a person is needed when the engine cannot name the stage", () => {
    const waiting = campaign({ status: "awaiting_approval" });

    expect(blockedReason(waiting)).toBe(
      "A stage is waiting for your approval.",
    );
  });

  it("is null when nothing blocks the campaign", () => {
    expect(blockedReason(campaign({ status: "running" }))).toBeNull();
  });
});

describe("toCampaignRow", () => {
  it("shows the same reason Home shows, or a dash when there is none", () => {
    const waiting = campaign({
      status: "awaiting_approval",
      blocked_stage_key: "creative-brief",
    });

    expect(toCampaignRow(waiting).next).toBe(
      "Creative brief is waiting for your approval.",
    );
    expect(toCampaignRow(campaign()).next).toBe("—");
  });
});
