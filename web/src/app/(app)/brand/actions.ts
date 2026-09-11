"use server";

import {
  markDnaReviewed,
  updateClarificationAnswer,
  type Clarification,
  type DnaReview,
} from "@/lib/engine";

/**
 * Saves a corrected answer to one Clarification.
 *
 * The edit is retrospective: it changes the Brand DNA every later campaign
 * reads and re-runs nothing already produced (ADR-0028).
 *
 * Args:
 *   clarificationId: The Clarification to re-answer.
 *   answer: The new answer.
 *
 * Returns:
 *   The Clarification as it now stands.
 */
export async function saveClarificationAnswer(
  clarificationId: string,
  answer: string,
): Promise<Clarification> {
  return updateClarificationAnswer(clarificationId, answer);
}

/**
 * Records that the business looked over its Brand DNA and found it still true.
 *
 * The Reviewed action. It clears the Review item on Home for another interval;
 * editing any answer does the same on its own (ADR-0028).
 *
 * Returns:
 *   The review as it now stands: not due.
 */
export async function markReviewed(): Promise<DnaReview> {
  return markDnaReviewed();
}
