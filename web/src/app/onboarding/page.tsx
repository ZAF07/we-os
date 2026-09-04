"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useWizard } from "@/components/wizard/use-wizard";
import { Field, WizardShell } from "@/components/wizard/wizard";
import type { Question, Questionnaire } from "@/lib/engine";
import {
  answersById,
  questionSteps,
  toAnswerPayload,
  unansweredRequired,
  type QuestionStep,
} from "@/lib/onboarding";

import { loadOnboarding, saveAnswers } from "./actions";

/** Input types rendered as a multi-line control rather than a single line. */
const MULTILINE_TYPES = new Set(["textarea", "list"]);

/**
 * Renders one published question as its labeled input.
 *
 * The control comes from the question's own `input_type`, and the
 * question's "why we ask" and help text are shown with it, so the
 * wizard explains every question without the frontend knowing what any
 * of them are (ADR-0018).
 *
 * Args:
 *   question: The published question to render.
 *   value: The answer entered so far.
 *   error: Whether to show the required-field error.
 *   onChange: Called with the new answer text.
 *
 * Returns:
 *   The field element.
 */
function QuestionField({
  question,
  value,
  error,
  onChange,
}: {
  question: Question;
  value: string;
  error: boolean;
  onChange: (value: string) => void;
}) {
  const control = {
    id: question.id,
    value,
    placeholder: question.help_text,
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => onChange(event.target.value),
  };
  return (
    <Field
      label={question.text}
      htmlFor={question.id}
      required={question.required}
      error={error}
      hint={`Why we ask: ${question.why_we_ask} · A good answer: ${question.help_text}`}
    >
      {MULTILINE_TYPES.has(question.input_type) ? (
        <Textarea {...control} />
      ) : (
        <Input {...control} />
      )}
    </Field>
  );
}

/** Renders the onboarding wizard from the published question set. */
export default function OnboardingPage() {
  const router = useRouter();

  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(
    null,
  );
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [newQuestions, setNewQuestions] = useState<string[]>([]);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    loadOnboarding()
      .then(({ questionnaire: published, dna, completeness }) => {
        setQuestionnaire(published);
        setAnswers(answersById(dna.answers));
        setNewQuestions(completeness.unanswered_new_questions);
      })
      .catch(() =>
        setFailure("We could not load your questions. Refresh to try again."),
      );
  }, []);

  const steps: QuestionStep[] = questionnaire
    ? questionSteps(questionnaire)
    : [];

  const stepIncomplete = (step: number) =>
    steps.length > 0 && unansweredRequired(steps[step], answers).length > 0;

  const persist = async () => {
    const payload = toAnswerPayload(answers);
    if (!payload.length) return;
    try {
      const report = await saveAnswers(payload);
      setNewQuestions(report.unanswered_new_questions);
      setFailure(null);
    } catch {
      setFailure("We could not save your answers. Check your connection.");
    }
  };

  const { step, attempted, back, next } = useWizard({
    stepCount: Math.max(steps.length, 1),
    isStepIncomplete: stepIncomplete,
    onFinish: () => {
      void persist().then(() => router.push("/brand"));
    },
  });

  if (!questionnaire) {
    return (
      <main className="flex-1 px-4 py-6 md:px-8 md:py-7">
        <p className="text-[13px] text-muted-foreground">
          {failure ?? "Loading your questions…"}
        </p>
      </main>
    );
  }

  const current = steps[step];
  const answered = Object.values(answers).filter((value) =>
    value.trim(),
  ).length;

  const progressNote =
    answered > 0
      ? `${answered} answered so far — saved as you go, so you can leave and come back.`
      : "Answers save as you go, so you can leave and come back.";

  /* A business whose answers predate a newer question set is prompted here,
     rather than being silently blocked by a gate that moved under them. */
  const newQuestionsNote = newQuestions.length
    ? `We have added ${newQuestions.length} new question${
        newQuestions.length === 1 ? "" : "s"
      } since you last answered — ${questionnaire.questions
        .filter((question) => newQuestions.includes(question.id))
        .map((question) => question.field)
        .join(", ")}. Answer ${
        newQuestions.length === 1 ? "it" : "them"
      } to keep your Brand DNA complete.`
    : null;

  return (
    <WizardShell
      title="Tell us about your business"
      subtitle="We only ask for facts you already know. Your positioning, messaging and channels are ours to produce — you approve them as the work goes."
      note={newQuestionsNote ?? progressNote}
      steps={steps.map((item) => item.name)}
      current={step}
      error={
        failure ??
        (attempted && stepIncomplete(step)
          ? "Fill in the required fields to continue."
          : undefined)
      }
      nextLabel="Finish onboarding"
      onBack={() => {
        void persist();
        back();
      }}
      onNext={() => {
        if (!stepIncomplete(step)) void persist();
        next();
      }}
    >
      {current.questions.map((question) => (
        <QuestionField
          key={question.id}
          question={question}
          value={answers[question.id] ?? ""}
          error={
            attempted &&
            question.required &&
            !(answers[question.id] ?? "").trim()
          }
          onChange={(value) =>
            setAnswers((previous) => ({ ...previous, [question.id]: value }))
          }
        />
      ))}
    </WizardShell>
  );
}
