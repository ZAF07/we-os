/**
 * Shared fixtures for the browser suite, and the one convention it must keep.
 *
 * The suite runs against a long-lived test tenant. The seed purges its
 * campaigns on every stack start, so a run against a freshly started stack sees
 * a clean list — but a *second* run against the same stack does not, because
 * every spec that creates a campaign leaves it behind.
 *
 * That makes the text a spec asserts on the sharp edge. A campaign name a
 * previous run also used matches two rows, and a `getByText` that resolved
 * uniquely the first time becomes a strict-mode violation the second. Minting
 * the text here is what stops it: a name from `uniqueName` belongs to the run
 * that created it, so asserting on it is safe however long the tenant lives.
 *
 * `eslint.config.mjs` refuses a `Date.now()` written inline in a spec, so the
 * convention has one home rather than a copy per spec and a note in someone's
 * head.
 */

let sequence = 0;

/**
 * Returns text unique to this run, for a spec that must assert on what it wrote.
 *
 * The timestamp separates runs; the counter separates values minted inside the
 * same millisecond, which one worker can easily do.
 *
 * Args:
 *   label: What the value is for, so a failure names something readable.
 *
 * Returns:
 *   The label followed by a run-unique suffix.
 */
export function uniqueName(label: string): string {
  sequence += 1;
  return `${label} ${Date.now()}-${sequence}`;
}
