"use server";

import { updateClarificationAnswer, type Clarification } from "@/lib/engine";

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
