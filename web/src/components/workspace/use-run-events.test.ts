import { describe, expect, it } from "vitest";

import { runningStage } from "@/components/workspace/use-run-events";

describe("runningStage", () => {
  it("names the stage the newest start began, until something ends it", () => {
    expect(runningStage([{ event: "gate.passed" }])).toBeNull();
    expect(
      runningStage([
        { event: "stage.start", stage: "research" },
        { event: "stage.review", stage: "research" },
      ]),
    ).toBe("research");
    expect(
      runningStage([
        { event: "stage.start", stage: "research" },
        { event: "stage.done", stage: "research" },
      ]),
    ).toBeNull();
  });

  it("follows the run from one stage to the next", () => {
    expect(
      runningStage([
        { event: "stage.start", stage: "research" },
        { event: "stage.done", stage: "research" },
        { event: "stage.start", stage: "brand-strategy" },
      ]),
    ).toBe("brand-strategy");
  });

  it("reads nothing running once the run summarises, whatever the outcome", () => {
    for (const outcome of ["ok", "error", "awaiting_approval"]) {
      expect(
        runningStage([
          { event: "stage.start", stage: "brand-strategy" },
          { event: "run.summary", outcome },
        ]),
      ).toBeNull();
    }
  });

  it("reads a revised stage as running again from its second start", () => {
    expect(
      runningStage([
        { event: "stage.start", stage: "brand-strategy" },
        { event: "run.summary", outcome: "awaiting_approval" },
        { event: "stage.revision_requested", stage: "brand-strategy" },
        { event: "stage.start", stage: "brand-strategy" },
      ]),
    ).toBe("brand-strategy");
  });
});
