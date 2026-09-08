import { describe, expect, it, vi } from "vitest";

import { resolveTransition } from "@/lib/wizard-transition";

/**
 * A save that records it was called and reports success.
 *
 * Returns:
 *   A spy standing in for a successful write.
 */
function savesFine() {
  return vi.fn(async () => true);
}

/**
 * A save that records it was called and reports failure.
 *
 * Returns:
 *   A spy standing in for a write the engine rejected.
 */
function savesBadly() {
  return vi.fn(async () => false);
}

describe("resolveTransition forwards", () => {
  it("refuses to leave a step whose required fields are missing", async () => {
    const save = savesFine();

    const outcome = await resolveTransition({
      direction: "forward",
      step: 0,
      stepCount: 5,
      isStepIncomplete: () => true,
      save,
    });

    expect(outcome).toEqual({ step: 0, attempted: true, finished: false });
    expect(save).not.toHaveBeenCalled();
  });

  it("saves once, then advances", async () => {
    const save = savesFine();

    const outcome = await resolveTransition({
      direction: "forward",
      step: 1,
      stepCount: 5,
      isStepIncomplete: () => false,
      save,
    });

    expect(outcome).toEqual({ step: 2, attempted: false, finished: false });
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("stays on the step when the save fails", async () => {
    const save = savesBadly();

    const outcome = await resolveTransition({
      direction: "forward",
      step: 1,
      stepCount: 5,
      isStepIncomplete: () => false,
      save,
    });

    expect(outcome).toEqual({ step: 1, attempted: null, finished: false });
  });

  it("leaves a revealed required-field error revealed when the save fails", async () => {
    const outcome = await resolveTransition({
      direction: "back",
      step: 2,
      stepCount: 5,
      isStepIncomplete: () => false,
      save: savesBadly(),
    });

    expect(outcome.attempted).toBeNull();
  });

  it("finishes on the last step after one save", async () => {
    const save = savesFine();

    const outcome = await resolveTransition({
      direction: "forward",
      step: 4,
      stepCount: 5,
      isStepIncomplete: () => false,
      save,
    });

    expect(outcome).toEqual({ step: 4, attempted: false, finished: true });
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("does not finish when the last step's save fails", async () => {
    const save = savesBadly();

    const outcome = await resolveTransition({
      direction: "forward",
      step: 4,
      stepCount: 5,
      isStepIncomplete: () => false,
      save,
    });

    expect(outcome).toEqual({ step: 4, attempted: null, finished: false });
  });
});

describe("resolveTransition backwards", () => {
  it("saves before stepping back", async () => {
    const save = savesFine();

    const outcome = await resolveTransition({
      direction: "back",
      step: 2,
      stepCount: 5,
      isStepIncomplete: () => true,
      save,
    });

    expect(outcome).toEqual({ step: 1, attempted: false, finished: false });
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("stays put when the save fails", async () => {
    const save = savesBadly();

    const outcome = await resolveTransition({
      direction: "back",
      step: 2,
      stepCount: 5,
      isStepIncomplete: () => false,
      save,
    });

    expect(outcome).toEqual({ step: 2, attempted: null, finished: false });
  });

  it("never steps below the first step", async () => {
    const outcome = await resolveTransition({
      direction: "back",
      step: 0,
      stepCount: 5,
      isStepIncomplete: () => false,
      save: savesFine(),
    });

    expect(outcome.step).toBe(0);
  });
});
