import { describe, expect, it } from "vitest";

import type { CampaignSummary, UsageReport } from "@/lib/engine";
import { progressWidth, toActiveCampaigns, toQueue, toStats } from "@/lib/home";

/**
 * Builds a campaign summary as the engine reports one.
 *
 * Args:
 *   id: The campaign slug.
 *   overrides: The fields this campaign differs from a fresh draft in.
 *
 * Returns:
 *   The summary.
 */
function campaign(
  id: string,
  overrides: Partial<CampaignSummary> = {},
): CampaignSummary {
  return {
    id,
    name: id,
    objective: "An objective",
    status: "draft",
    stage_progress: { completed: 0, total: 6, current_stage_key: "research" },
    blocked_reason: null,
    ...overrides,
  };
}

describe("toQueue", () => {
  it("lists only campaigns that actually need a person", () => {
    const queue = toQueue([
      campaign("running-fine", { status: "running" }),
      campaign("needs-me", {
        status: "awaiting_approval",
        blocked_reason: "Strategy is waiting for your approval.",
      }),
    ]);

    expect(queue).toHaveLength(1);
    expect(queue[0].slug).toBe("needs-me");
  });

  it("puts approvals before stale work, because an approval blocks a run", () => {
    const queue = toQueue([
      campaign("stale-one", {
        status: "running",
        blocked_reason: "Plan rests on a decision you have since re-opened.",
      }),
      campaign("gate-one", {
        status: "awaiting_approval",
        blocked_reason: "Strategy is waiting for your approval.",
      }),
    ]);

    expect(queue.map((item) => item.slug)).toEqual(["gate-one", "stale-one"]);
    expect(queue[0].tag).toBe("Decision");
    expect(queue[1].tag).toBe("Stale");
  });

  it("shows the engine's own reason rather than inventing one", () => {
    const queue = toQueue([
      campaign("c", {
        status: "awaiting_approval",
        blocked_reason: "Strategy is waiting for your approval.",
      }),
    ]);

    expect(queue[0].title).toBe("Strategy is waiting for your approval.");
  });

  it("is empty when nothing needs anyone", () => {
    expect(toQueue([campaign("a"), campaign("b")])).toEqual([]);
  });
});

describe("toStats", () => {
  const usage: UsageReport = {
    used: 25,
    allowance: 100,
    remaining: 75,
    exhausted: false,
    campaigns: [],
  };

  it("counts what needs a person and what is running", () => {
    const stats = toStats(
      [
        campaign("a", {
          status: "awaiting_approval",
          blocked_reason: "waiting",
        }),
        campaign("b", { status: "running" }),
        campaign("c"),
      ],
      usage,
    );

    expect(stats[0]).toMatchObject({ label: "Need you", value: "1" });
    expect(stats[1]).toMatchObject({ label: "In progress", value: "1" });
  });

  it("shows allowance as a percentage, flagged once it is spent", () => {
    const healthy = toStats([], usage);
    expect(healthy[2]).toMatchObject({ value: "25%", tone: "default" });

    const spent = toStats([], {
      ...usage,
      used: 100,
      remaining: 0,
      exhausted: true,
    });
    expect(spent[2]).toMatchObject({ value: "100%", tone: "destructive" });
  });

  it("reports raw spend when the allowance is unlimited", () => {
    const stats = toStats([], { ...usage, allowance: 0 });
    expect(stats[2].value).toBe("25.00");
  });

  it("omits the allowance tile when usage could not be read", () => {
    expect(toStats([campaign("a")], null)).toHaveLength(2);
  });
});

describe("toActiveCampaigns", () => {
  it("leaves out drafts, which have not started", () => {
    const active = toActiveCampaigns([
      campaign("draft-one"),
      campaign("started", { status: "running" }),
    ]);

    expect(active.map((entry) => entry.slug)).toEqual(["started"]);
  });

  it("carries progress in the operator's vocabulary", () => {
    const active = toActiveCampaigns([
      campaign("c", {
        status: "awaiting_approval",
        stage_progress: {
          completed: 2,
          total: 6,
          current_stage_key: "brand-strategy",
        },
      }),
    ]);

    expect(active[0].status).toBe("Ready for review");
    expect(active[0].stageNote).toBe("2/6 stages");
  });
});

describe("progressWidth", () => {
  it("renders progress as a percentage", () => {
    expect(progressWidth(3, 6)).toBe("50%");
    expect(progressWidth(0, 6)).toBe("0%");
    expect(progressWidth(6, 6)).toBe("100%");
  });

  it("does not divide by zero when a campaign reports no stages", () => {
    expect(progressWidth(0, 0)).toBe("0%");
  });
});
