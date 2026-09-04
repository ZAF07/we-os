import { describe, expect, it } from "vitest";

import type { CampaignStage } from "@/lib/engine";
import {
  defaultStageKey,
  deliverableName,
  stageAwaitingApproval,
  stageStatus,
  stageTitle,
  toPhases,
} from "@/lib/workspace";

/**
 * Builds a stage as the engine reports one.
 *
 * Args:
 *   key: The engine stage key.
 *   phase: The operator Phase the stage belongs to.
 *   overrides: The fields this stage differs from a pending stage in.
 *
 * Returns:
 *   The stage.
 */
function stage(
  key: string,
  phase: string,
  overrides: Partial<CampaignStage> = {},
): CampaignStage {
  return {
    key,
    phase,
    state: "pending",
    approval_policy: "human",
    latest_version: null,
    stale: false,
    ...overrides,
  };
}

describe("toPhases", () => {
  it("groups the two Strategy stages under one Phase", () => {
    const phases = toPhases([
      stage("research", "Research"),
      stage("brand-strategy", "Strategy"),
      stage("campaign-strategy", "Strategy"),
      stage("performance-plan", "Plan"),
    ]);

    expect(phases.map((phase) => phase.name)).toEqual([
      "Research",
      "Strategy",
      "Plan",
    ]);
    expect(phases[1].stages.map((s) => s.key)).toEqual([
      "brand-strategy",
      "campaign-strategy",
    ]);
  });

  it("reads a Phase as Ready for review when any stage under it is at a gate", () => {
    const phases = toPhases([
      stage("brand-strategy", "Strategy", {
        state: "completed",
        latest_version: 1,
      }),
      stage("campaign-strategy", "Strategy", { state: "awaiting_approval" }),
    ]);

    expect(phases[0].status).toBe("Ready for review");
  });

  it("reads a Phase as Approved only once every stage under it has completed", () => {
    const partial = toPhases([
      stage("brand-strategy", "Strategy", {
        state: "completed",
        latest_version: 1,
      }),
      stage("campaign-strategy", "Strategy"),
    ]);
    expect(partial[0].status).toBe("In progress");

    const whole = toPhases([
      stage("brand-strategy", "Strategy", {
        state: "completed",
        latest_version: 1,
      }),
      stage("campaign-strategy", "Strategy", {
        state: "completed",
        latest_version: 1,
      }),
    ]);
    expect(whole[0].status).toBe("Approved");
  });

  it("reads a Phase as Stale when work under it rests on a re-opened decision", () => {
    const phases = toPhases([
      stage("performance-plan", "Plan", {
        state: "stale",
        stale: true,
        latest_version: 2,
      }),
    ]);

    expect(phases[0].status).toBe("Stale");
  });

  it("prefers the gate over staleness, because the gate is the live decision", () => {
    const phases = toPhases([
      stage("creative-brief", "Produce", { state: "awaiting_approval" }),
      stage("asset-prompts", "Produce", { stale: true, latest_version: 1 }),
    ]);

    expect(phases[0].status).toBe("Ready for review");
  });
});

describe("stageStatus", () => {
  it("speaks the operator's vocabulary, never the engine's state string", () => {
    expect(stageStatus("pending")).toBe("Not started");
    expect(stageStatus("completed")).toBe("Approved");
    expect(stageStatus("awaiting_approval")).toBe("Ready for review");
    expect(stageStatus("stale")).toBe("Stale");
  });

  it("falls back to Not started rather than rendering an unknown engine state", () => {
    expect(stageStatus("something-new")).toBe("Not started");
  });
});

describe("stageTitle and deliverableName", () => {
  it("names every pipeline stage in the operator's words", () => {
    expect(stageTitle("brand-strategy")).toBe("Brand strategy");
    expect(stageTitle("asset-prompts")).toBe("Asset prompts");
  });

  it("addresses each stage's deliverable by the filename the engine writes", () => {
    expect(deliverableName("research")).toBe("research.md");
    expect(deliverableName("performance-plan")).toBe("performance-plan.md");
  });
});

describe("defaultStageKey", () => {
  it("opens on the stage holding at a gate, which is the decision to make", () => {
    const stages = [
      stage("research", "Research", { state: "completed", latest_version: 1 }),
      stage("brand-strategy", "Strategy", { state: "awaiting_approval" }),
      stage("campaign-strategy", "Strategy"),
    ];

    expect(defaultStageKey(stages)).toBe("brand-strategy");
    expect(stageAwaitingApproval(stages)?.key).toBe("brand-strategy");
  });

  it("opens on the newest thing produced when nothing is waiting", () => {
    const stages = [
      stage("research", "Research", { state: "completed", latest_version: 1 }),
      stage("brand-strategy", "Strategy", {
        state: "completed",
        latest_version: 2,
      }),
      stage("campaign-strategy", "Strategy"),
    ];

    expect(defaultStageKey(stages)).toBe("brand-strategy");
  });

  it("opens on the first stage of a campaign that has produced nothing", () => {
    const stages = [
      stage("research", "Research"),
      stage("brand-strategy", "Strategy"),
    ];

    expect(defaultStageKey(stages)).toBe("research");
    expect(stageAwaitingApproval(stages)).toBeNull();
  });

  it("has no stage to open on when the campaign reports none", () => {
    expect(defaultStageKey([])).toBeNull();
  });
});
