"use server";

import { EngineError, engineErrorMessage, setTenantTier } from "@/lib/engine";

export interface RecordTierResult {
  error: string | null;
  retryable: boolean;
}

/**
 * Records the chosen tier against the business the session now carries.
 *
 * Called once the Organization exists and is active on the session, so the
 * engine mints the tenant from the verified claim and attaches the tier to it
 * (ADR-0027). Safe to repeat: after a failure the retry is this call alone,
 * and the engine accepts the same tier again without changing anything.
 *
 * Args:
 *   tier: The tier name as the tier card sent it.
 *
 * Returns:
 *   No error when the tier is recorded, otherwise the engine's own message,
 *   returned rather than thrown so the page can show it beside a retry. The
 *   one refusal no retry can change — the business already has a different
 *   tier — is marked not retryable, so the page offers Home instead.
 */
export async function recordTier(tier: string): Promise<RecordTierResult> {
  try {
    await setTenantTier(tier);
    return { error: null, retryable: true };
  } catch (error) {
    const alreadySet =
      error instanceof EngineError && error.type === "tier_already_set";
    return { error: engineErrorMessage(error), retryable: !alreadySet };
  }
}
