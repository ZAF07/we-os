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
 * The save is awaited and its result decides the move, so a step is never
 * left before its answers are written. Optimistic advancement is what let
 * two saves run at once and the staler one overwrite the fresher, which is
 * the bug this rule exists to prevent.
 *
 * A step whose Required fields are missing is not saved and not left; it
 * only raises the attempted flag that reveals the field errors. Moving back
 * saves whatever has been entered — blanks are dropped by the payload
 * builder, so a half-filled step writes only its real answers.
 *
 * A failed save leaves the attempted flag alone rather than lowering it, so
 * a required-field error already on screen is not cleared by a write that
 * never landed.
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
  const moved = { step, attempted: false, finished: false };

  if (direction === "forward" && isStepIncomplete(step)) {
    return { step, attempted: true, finished: false };
  }
  if (!(await save())) {
    return { step, attempted: null, finished: false };
  }

  if (direction === "back") {
    return { ...moved, step: Math.max(0, step - 1) };
  }
  if (step < stepCount - 1) {
    return { ...moved, step: step + 1 };
  }
  return { ...moved, finished: true };
}
