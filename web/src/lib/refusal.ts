import { EngineError } from "@/lib/engine-error";

/**
 * Turns an engine failure into the message the Workspace shows.
 *
 * The engine explains a refusal in the operator's terms, so its message is
 * surfaced as-is rather than replaced by a generic one. Two refusals carry
 * detail the message alone leaves out, and both are the kind a person can act
 * on, so the numbers are put back:
 *
 * - A failed **DNA Gate** says only that the gate failed; what the person needs
 *   is the list of fields it named.
 * - An **exhausted allowance** says work has stopped; what they need is how far
 *   past the line they are, since that is what tells them whether to wait for a
 *   renewal or ask for more (ADR-0020).
 *
 * Args:
 *   error: The failure raised while calling the engine.
 *
 * Returns:
 *   The message to render.
 *
 * Throws:
 *   Error: Anything that is not an engine failure, which is a real fault.
 */
export function refusalMessage(error: unknown): string {
  if (!(error instanceof EngineError)) throw error;

  if (error.type === "quota_exhausted") {
    const { used, allowance } = error.detail;
    if (typeof used === "number" && typeof allowance === "number") {
      return `${error.message} You have used ${used.toFixed(2)} of ${allowance.toFixed(2)}.`;
    }
    return error.message;
  }

  const missing = error.detail.missing_fields;
  if (Array.isArray(missing) && missing.length > 0) {
    return `${error.message} Still needed: ${missing.join("; ")}`;
  }

  return error.message;
}
