import type { DnaAnswer, Question, Questionnaire } from "@/lib/engine";
import { BRAND_SECTIONS, type BrandSection } from "@/lib/mock-data";

/** The question whose answer lists the audience segments campaigns target. */
const AUDIENCE_QUESTION_ID = "q_segments";

/** Separates a written entry's name from its detail on one line. */
const LINE_SEPARATOR = /\s+[—–-]\s+/;

/** Stands in for the business name in section descriptions. */
const BUSINESS_LABEL = "your business";

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

/**
 * Returns the audience segment names campaigns can target.
 *
 * The segments live in the Brand DNA answer to the audience question,
 * one per line. Until the Campaign screens are wired to the engine
 * (tracked separately), the fixture segments stand in when the business
 * has not answered that question.
 *
 * Args:
 *   answers: Answer text keyed by question id, or null before onboarding.
 *
 * Returns:
 *   The segment names to offer.
 */
export function audienceSegmentOptions(
  answers: Record<string, string> | null,
): string[] {
  const written = (answers?.[AUDIENCE_QUESTION_ID] ?? "")
    .split("\n")
    .map((line) => line.trim().replace(/^[-*]\s*/, ""))
    .map((line) => line.split(LINE_SEPARATOR)[0].trim())
    .filter(Boolean);
  if (written.length) return written;

  const fixture = BRAND_SECTIONS.find(
    (section) => section.name === "Audience segments",
  );
  return (fixture?.entries ?? []).map((entry) =>
    entry.k.replace(/^\d+\s*·\s*/, ""),
  );
}

/**
 * Builds the Brand screen sections, overlaying the business's own Brand
 * DNA answers on the fixture sections.
 *
 * Only the sections the questionnaire actually covers are replaced; the
 * rest remain fixtures until the Brand screen is wired to the engine.
 *
 * Args:
 *   questionnaire: The published question set, or null before it loads.
 *   answers: Answer text keyed by question id, or null before onboarding.
 *
 * Returns:
 *   The brand sections to render.
 */
export function brandSectionsWithOnboarding(
  questionnaire: Questionnaire | null,
  answers: Record<string, string> | null,
): BrandSection[] {
  if (!questionnaire || !answers) return BRAND_SECTIONS;

  const answered = questionnaire.questions.filter((question) =>
    (answers[question.id] ?? "").trim(),
  );
  if (!answered.length) return BRAND_SECTIONS;

  const fromDna: BrandSection[] = questionSteps({
    ...questionnaire,
    questions: answered,
  }).map((step) => ({
    name: step.name,
    verified: "Just now",
    desc: `What ${BUSINESS_LABEL} told us about ${step.name.toLowerCase()}.`,
    entries: step.questions.map((question) => ({
      k: question.field,
      v: answers[question.id],
    })),
  }));

  const covered = new Set(fromDna.map((section) => section.name));
  return [
    ...fromDna,
    ...BRAND_SECTIONS.filter((section) => !covered.has(section.name)),
  ];
}
