"use server";

import { engineErrorMessage, setTenantTier } from "@/lib/engine";

export interface RecordTierResult {
  error: string | null;
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
 *   returned rather than thrown so the page can show it beside a retry.
 */
export async function recordTier(tier: string): Promise<RecordTierResult> {
  try {
    await setTenantTier(tier);
    return { error: null };
  } catch (error) {
    return { error: engineErrorMessage(error) };
  }
}
