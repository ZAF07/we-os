"use client";

import { useRef, useState } from "react";

import {
  resolveTransition,
  type TransitionDirection,
} from "@/lib/wizard-transition";

/**
 * Drives a multi-step wizard: step position, validated advancement, the
 * attempted flag that reveals required-field errors, and the in-flight flag
 * that disables the buttons while a step's save is running.
 *
 * Every transition awaits `save`, so two saves are never in flight at once.
 * Forward moves only if the save succeeded, so a step is never advanced
 * past before its answers are written; Back moves either way, so a failing
 * write never leaves the business with nowhere to go. A wizard with nothing
 * to persist passes a `save` that succeeds immediately.
 *
 * The in-flight guard reads a ref rather than the busy state, because a
 * click can land before React has re-rendered the disabled button. Dropping
 * that click is deliberate: a second save queued behind the first is the
 * race this hook exists to remove.
 *
 * Args:
 *   stepCount: Total number of steps.
 *   isStepIncomplete: Returns true when the given step's required
 *     inputs are missing.
 *   save: Writes the answers entered so far, returning whether it
 *     succeeded. A failed save leaves the wizard where it is when moving
 *     forward, and is no obstacle to moving back.
 *   onFinish: Called when the final step's save has succeeded.
 *
 * Returns:
 *   The current step, the attempted and busy flags, and back/next handlers.
 *   Each handler resolves once its transition has settled, so a caller with
 *   something to do afterwards can await it.
 */
export function useWizard({
  stepCount,
  isStepIncomplete,
  save,
  onFinish,
}: {
  stepCount: number;
  isStepIncomplete: (step: number) => boolean;
  save: () => Promise<boolean>;
  onFinish: () => void;
}) {
  const [step, setStep] = useState(0);
  const [attempted, setAttempted] = useState(false);
  const [busy, setBusy] = useState(false);
  const saving = useRef(false);

  const move = async (direction: TransitionDirection) => {
    if (saving.current) return;
    saving.current = true;
    setBusy(true);
    try {
      const outcome = await resolveTransition({
        direction,
        step,
        stepCount,
        isStepIncomplete,
        save,
      });
      if (outcome.attempted !== null) setAttempted(outcome.attempted);
      setStep(outcome.step);
      if (outcome.finished) onFinish();
    } finally {
      saving.current = false;
      setBusy(false);
    }
  };

  return {
    step,
    attempted,
    busy,
    back: () => move("back"),
    next: () => move("forward"),
  };
}
