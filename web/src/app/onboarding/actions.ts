"use server";

import {
  getBrandDna,
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
}

/**
 * Loads what the wizard renders: the published question set and the
 * answers already saved, so onboarding resumes where it was left.
 *
 * Returns:
 *   The published questionnaire and the tenant's Brand DNA.
 */
export async function loadOnboarding(): Promise<OnboardingState> {
  const [questionnaire, dna] = await Promise.all([
    getQuestionnaire(),
    getBrandDna(),
  ]);
  return { questionnaire, dna };
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
