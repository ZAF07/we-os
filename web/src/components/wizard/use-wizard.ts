"use client";

import { useState } from "react";

/**
 * Drives a multi-step wizard: step position, validated advancement,
 * and the attempted flag that reveals required-field errors.
 *
 * Args:
 *   stepCount: Total number of steps.
 *   isStepIncomplete: Returns true when the given step's required
 *     inputs are missing.
 *   onFinish: Called when Next is confirmed on the final step.
 *
 * Returns:
 *   The current step, the attempted flag, and back/next handlers.
 */
export function useWizard({
  stepCount,
  isStepIncomplete,
  onFinish,
}: {
  stepCount: number;
  isStepIncomplete: (step: number) => boolean;
  onFinish: () => void;
}) {
  const [step, setStep] = useState(0);
  const [attempted, setAttempted] = useState(false);

  const back = () => {
    setAttempted(false);
    setStep((current) => Math.max(0, current - 1));
  };

  const next = () => {
    if (isStepIncomplete(step)) {
      setAttempted(true);
      return;
    }
    setAttempted(false);
    if (step < stepCount - 1) {
      setStep(step + 1);
      return;
    }
    onFinish();
  };

  return { step, attempted, back, next };
}
