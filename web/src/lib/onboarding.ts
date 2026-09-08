import type { DnaAnswer, Question, Questionnaire } from "@/lib/engine";

export interface QuestionStep {
  name: string;
  questions: Question[];
}

/**
 * Groups the published questions into wizard steps, one per Brand DNA
 * section, preserving the order the questionnaire asks them in.
 *
 * The wizard derives its steps from the question set rather than
 * hardcoding them, so publishing a new version reshapes onboarding with
 * no frontend change (ADR-0018).
 *
 * Args:
 *   questionnaire: The published question set.
 *
 * Returns:
 *   One step per section, in first-asked order.
 */
export function questionSteps(questionnaire: Questionnaire): QuestionStep[] {
  const steps: QuestionStep[] = [];
  for (const question of questionnaire.questions) {
    const existing = steps.find((step) => step.name === question.section);
    if (existing) {
      existing.questions.push(question);
      continue;
    }
    steps.push({ name: question.section, questions: [question] });
  }
  return steps;
}

/**
 * Builds the answer lookup the wizard edits, seeded from what was saved.
 *
 * Args:
 *   answers: The answers already stored for the business.
 *
 * Returns:
 *   Answer text keyed by question id.
 */
export function answersById(answers: DnaAnswer[]): Record<string, string> {
  return Object.fromEntries(
    answers.map((answer) => [answer.question_id, answer.answer]),
  );
}

/**
 * Returns the Required questions in a step that have no answer yet.
 *
 * Args:
 *   step: The wizard step to check.
 *   answers: Answer text keyed by question id.
 *
 * Returns:
 *   The unanswered Required questions, which block advancing.
 */
export function unansweredRequired(
  step: QuestionStep,
  answers: Record<string, string>,
): Question[] {
  return step.questions.filter(
    (question) => question.required && !(answers[question.id] ?? "").trim(),
  );
}

/**
 * Converts the wizard's answer lookup into the payload the engine takes,
 * dropping blanks so an untouched field is never saved as an answer.
 *
 * Args:
 *   answers: Answer text keyed by question id.
 *
 * Returns:
 *   One entry per non-blank answer.
 */
export function toAnswerPayload(answers: Record<string, string>): DnaAnswer[] {
  return Object.entries(answers)
    .filter(([, answer]) => answer.trim())
    .map(([question_id, answer]) => ({ question_id, answer: answer.trim() }));
}
