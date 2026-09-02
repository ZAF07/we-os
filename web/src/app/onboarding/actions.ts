"use server";

import {
  getBrandDna,
  getBrandDnaCompleteness,
  getQuestionnaire,
  saveBrandDnaAnswers,
  type BrandDna,
  type DnaAnswer,
  type DnaCompleteness,
  type Questionnaire,
} from "@/lib/engine";

export interface OnboardingState {
  questionnaire: Questionnaire;
  dna: BrandDna;
  completeness: DnaCompleteness;
}

/**
 * Loads what the wizard renders: the published question set, the answers
 * already saved so onboarding resumes where it was left, and the
 * completeness report, which names any question a newer published
 * version added that this business has not been shown.
 *
 * Returns:
 *   The published questionnaire, the tenant's Brand DNA, and its
 *   completeness report.
 */
export async function loadOnboarding(): Promise<OnboardingState> {
  const [questionnaire, dna, completeness] = await Promise.all([
    getQuestionnaire(),
    getBrandDna(),
    getBrandDnaCompleteness(),
  ]);
  return { questionnaire, dna, completeness };
}

/**
 * Saves the answers entered so far and reports what remains.
 *
 * Args:
 *   answers: The answers to upsert.
 *
 * Returns:
 *   The updated completeness report.
 */
export async function saveAnswers(
  answers: DnaAnswer[],
): Promise<DnaCompleteness> {
  return saveBrandDnaAnswers(answers);
}
