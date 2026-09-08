/** Which way the wizard is being asked to move. */
export type TransitionDirection = "forward" | "back";

/** What a transition needs to know to decide where the wizard lands. */
export interface TransitionRequest {
  direction: TransitionDirection;
  step: number;
  stepCount: number;
  isStepIncomplete: (step: number) => boolean;
  save: () => Promise<boolean>;
}

/**
 * Where a transition lands.
 *
 * `attempted` is null when the transition has nothing to say about the
 * required-field errors, which leaves whatever the wizard was already
 * showing in place.
 */
export interface TransitionOutcome {
  step: number;
  attempted: boolean | null;
  finished: boolean;
}

/**
 * Decides where a wizard transition lands, saving before it moves.
 *
 * The save is always awaited, so two saves are never in flight at once and
 * the staler one can never overwrite the fresher — the race this rule
 * exists to prevent.
 *
 * Going forward, the save's result decides the move: a step is never
 * advanced past before its answers are written. A step whose Required
 * fields are missing is not saved and not left; it only raises the
 * attempted flag that reveals the field errors. A failed save leaves the
 * attempted flag alone rather than lowering it, so a required-field error
 * already on screen is not cleared by a write that never landed.
 *
 * Going back moves whether or not the save landed. Re-reading an earlier
 * answer does not depend on the current step having been written, and a
 * blocked Back leaves a business on a flaky connection with no button that
 * moves them anywhere. The answers stay in state, so the next save that
 * succeeds writes them. Moving back saves whatever has been entered —
 * blanks are dropped by the payload builder, so a half-filled step writes
 * only its real answers.
 *
 * Going back says nothing about the required-field errors either way. It
 * neither reveals them, having demanded nothing, nor clears ones already on
 * screen, which no unfilled field was filled to earn.
 *
 * Args:
 *   direction: Whether the wizard is moving forward or back.
 *   step: The step the wizard is on.
 *   stepCount: Total number of steps.
 *   isStepIncomplete: Returns true when a step's Required inputs are missing.
 *   save: Writes the answers entered so far, returning whether it succeeded.
 *
 * Returns:
 *   The step to land on, whether to reveal required-field errors (null to
 *   leave them as they are), and whether the wizard has finished its last
 *   step.
 */
export async function resolveTransition({
  direction,
  step,
  stepCount,
  isStepIncomplete,
  save,
}: TransitionRequest): Promise<TransitionOutcome> {
  if (direction === "back") {
    await save();
    return { step: Math.max(0, step - 1), attempted: null, finished: false };
  }

  if (isStepIncomplete(step)) {
    return { step, attempted: true, finished: false };
  }
  if (!(await save())) {
    return { step, attempted: null, finished: false };
  }

  const saved = { step, attempted: false, finished: false };
  if (step < stepCount - 1) {
    return { ...saved, step: step + 1 };
  }
  return { ...saved, finished: true };
}
