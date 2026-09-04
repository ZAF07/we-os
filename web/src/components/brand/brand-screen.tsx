"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { StatusPill } from "@/components/ui/status-pill";
import type {
  BrandDna,
  DnaCompleteness,
  Question,
  Questionnaire,
} from "@/lib/engine";
import { questionSteps } from "@/lib/onboarding";
import { cn } from "@/lib/utils";

import { saveAnswers } from "@/app/onboarding/actions";

/**
 * Renders the Brand screen: the business's own Brand DNA, editable answer by
 * answer.
 *
 * The Brand DNA is the thing every recommendation is grounded in, and it is
 * **authored by the business** — never drafted or guessed by a model
 * (ADR-0018). So this screen is an editor over the questionnaire's own
 * questions, not a rendering of prose: what is shown is what was answered, and
 * changing it is changing the answer.
 *
 * Args:
 *   questionnaire: The published question set, which defines the sections.
 *   dna: The business's saved answers.
 *   completeness: Which Required answers are still owed.
 */
export function BrandScreen({
  questionnaire,
  dna,
  completeness,
}: {
  questionnaire: Questionnaire;
  dna: BrandDna;
  completeness: DnaCompleteness;
}) {
  const router = useRouter();
  const sections = questionSteps(questionnaire);
  const [selected, setSelected] = useState(0);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startSaving] = useTransition();

  const answers = new Map(
    dna.answers.map((answer) => [answer.question_id, answer.answer]),
  );
  const missing = new Set(
    completeness.missing.map((field) => field.question_id),
  );
  const section = sections[selected] ?? sections[0];

  const save = (questionId: string) => {
    setError(null);
    startSaving(async () => {
      try {
        await saveAnswers([{ question_id: questionId, answer: draft.trim() }]);
        setEditing(null);
        router.refresh();
      } catch {
        setError("Could not save that answer. Try again.");
      }
    });
  };

  if (section === undefined) {
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
        <h1 className="text-xl font-bold tracking-tight">Brand</h1>
        <p className="mt-2 text-[13px] text-muted-foreground">
          No question set is published yet, so there is nothing to answer.
        </p>
      </main>
    );
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden lg:flex-row">
      <div className="shrink-0 border-b bg-card lg:w-[224px] lg:overflow-y-auto lg:border-r lg:border-b-0">
        <div className="px-4 pt-4 pb-1 text-[11px] font-bold tracking-wider text-slate-400 uppercase lg:px-5 lg:pt-5 lg:pb-2.5">
          Brand source of truth
        </div>
        <nav
          aria-label="Brand sections"
          className="scrollbar-none flex gap-1 overflow-x-auto px-2.5 pb-3 lg:flex-col lg:gap-0 lg:pb-5"
        >
          {sections.map((item, index) => {
            const owed = item.questions.filter((question) =>
              missing.has(question.id),
            ).length;
            return (
              <button
                key={item.name}
                onClick={() => setSelected(index)}
                className={cn(
                  "flex w-auto cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-[7px] text-left text-[13px] whitespace-nowrap lg:w-full lg:whitespace-normal",
                  selected === index
                    ? "bg-indigo-50 font-semibold text-primary"
                    : "font-medium text-slate-700 hover:bg-slate-100",
                )}
              >
                <span className="flex-1">{item.name}</span>
                {owed > 0 && (
                  <span className="rounded-full bg-amber-100 px-1.5 text-[10.5px] font-bold text-amber-800">
                    {owed}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
        <div className="max-w-[680px]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h1 className="text-xl font-bold tracking-tight">{section.name}</h1>
            <StatusPill
              status={completeness.complete ? "Approved" : "Needs input"}
            />
          </div>
          <p className="mt-1.5 mb-[18px] text-[13px] text-muted-foreground">
            {completeness.complete
              ? `Every Required answer is in — ${completeness.required_answered} of ${completeness.required_total}. Campaigns can run.`
              : `${completeness.required_answered} of ${completeness.required_total} Required answers are in. Campaigns cannot run until the rest are.`}
          </p>

          {error && (
            <p
              role="alert"
              className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
            >
              {error}
            </p>
          )}

          <div className="flex flex-col gap-3">
            {section.questions.map((question) => (
              <AnswerCard
                key={question.id}
                question={question}
                answer={answers.get(question.id) ?? ""}
                owed={missing.has(question.id)}
                editing={editing === question.id}
                draft={draft}
                pending={pending}
                onEdit={() => {
                  setEditing(question.id);
                  setDraft(answers.get(question.id) ?? "");
                  setError(null);
                }}
                onDraft={setDraft}
                onCancel={() => setEditing(null)}
                onSave={() => save(question.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

/**
 * Renders one question and its answer, editable in place.
 *
 * Args:
 *   question: The question as the published set asks it.
 *   answer: What the business answered, empty when it has not.
 *   owed: Whether this is a Required answer still missing.
 *   editing: Whether this card is the one being edited.
 *   draft: The text being typed, when editing.
 *   pending: Whether a save is in flight.
 *   onEdit: Starts editing this answer.
 *   onDraft: Records a keystroke.
 *   onCancel: Abandons the edit.
 *   onSave: Saves the draft.
 */
function AnswerCard({
  question,
  answer,
  owed,
  editing,
  draft,
  pending,
  onEdit,
  onDraft,
  onCancel,
  onSave,
}: {
  question: Question;
  answer: string;
  owed: boolean;
  editing: boolean;
  draft: string;
  pending: boolean;
  onEdit: () => void;
  onDraft: (value: string) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <div className="rounded-xl border bg-card px-[18px] py-[15px]">
      <div className="flex items-start gap-2">
        <div className="flex-1 text-[13.5px] font-bold">{question.text}</div>
        {owed && (
          <span className="rounded-[5px] bg-amber-100 px-[7px] py-px text-[10.5px] font-bold text-amber-800">
            REQUIRED
          </span>
        )}
      </div>
      <div className="mt-0.5 text-[11.5px] text-muted-foreground">
        {question.why_we_ask}
      </div>

      {editing ? (
        <div className="mt-2.5">
          <label htmlFor={`answer-${question.id}`} className="sr-only">
            {question.text}
          </label>
          <textarea
            id={`answer-${question.id}`}
            value={draft}
            onChange={(event) => onDraft(event.target.value)}
            rows={question.input_type === "textarea" ? 4 : 2}
            className="w-full rounded-lg border bg-card px-2.5 py-2 text-[13px]"
          />
          <div className="mt-2 flex gap-2">
            <button
              onClick={onSave}
              disabled={pending}
              className="cursor-pointer rounded-lg bg-primary px-3 py-1.5 text-[12.5px] font-semibold text-primary-foreground hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pending ? "Saving…" : "Save"}
            </button>
            <button
              onClick={onCancel}
              disabled={pending}
              className="cursor-pointer rounded-lg border bg-card px-3 py-1.5 text-[12.5px] font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-1.5 flex items-start gap-2">
          <div className="flex-1 text-[13.5px] whitespace-pre-wrap text-slate-700">
            {answer === "" ? (
              <span className="text-muted-foreground italic">
                Not answered yet.
              </span>
            ) : (
              answer
            )}
          </div>
          <button
            onClick={onEdit}
            aria-label={`Edit: ${question.text}`}
            className="shrink-0 cursor-pointer rounded-md px-2 py-1 text-[12.5px] font-semibold text-primary hover:bg-indigo-50"
          >
            Edit
          </button>
        </div>
      )}
    </div>
  );
}
