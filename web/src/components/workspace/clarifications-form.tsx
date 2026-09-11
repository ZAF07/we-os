"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { ActionResult } from "@/app/(app)/campaigns/[slug]/clarifications/actions";
import type { ClarificationAnswer, RunClarifications } from "@/lib/engine";
import { stageTitle } from "@/lib/workspace";

/**
 * Renders the questions a specialist stopped to ask, each with an answer box.
 *
 * All of a stage's questions are answered together, since the stage re-runs
 * once from a Brand DNA that carries every answer (ADR-0028); the button stays
 * off until each has one. Each question carries the specialist's reason, so
 * the owner knows why it is asked and can give a useful answer. Once the
 * answers are in, the page moves to the Workspace, which follows the run to
 * its next gate.
 *
 * Args:
 *   slug: The campaign the run belongs to.
 *   pending: What the run is asking, and which stage asked.
 *   submit: Sends the answers; resolves with the engine's refusal, if any.
 */
export function ClarificationsForm({
  slug,
  pending,
  submit,
}: {
  slug: string;
  pending: RunClarifications;
  submit: (
    slug: string,
    runId: string,
    answers: ClarificationAnswer[],
  ) => Promise<ActionResult>;
}) {
  const router = useRouter();
  const [answers, setAnswers] = useState<string[]>(() =>
    pending.questions.map(() => ""),
  );
  const [error, setError] = useState<string | null>(null);
  const [sending, startSending] = useTransition();
  const complete = answers.every((answer) => answer.trim() !== "");

  const send = () => {
    setError(null);
    startSending(async () => {
      const result = await submit(
        slug,
        pending.run_id,
        pending.questions.map((item, index) => ({
          question: item.question,
          answer: answers[index].trim(),
        })),
      );
      if (result.error) {
        setError(result.error);
        return;
      }
      router.push(`/campaigns/${slug}`);
    });
  };

  return (
    <div className="mt-2 max-w-[720px]">
      <p className="text-[13px] text-muted-foreground">
        {stageTitle(pending.stage)} paused because it needs facts about your
        business that your Brand DNA does not carry. Nothing is written on a
        guess: the run continues once these are answered, and your answers are
        saved to your Brand DNA so no later campaign asks again.
      </p>
      <ol
        aria-label="Questions"
        className="mt-5 flex flex-col gap-3 rounded-xl border bg-card"
      >
        {pending.questions.map((item, index) => {
          const id = `clarification-${index}`;
          return (
            <li
              key={item.question}
              className="border-b border-slate-100 px-[18px] py-3.5 last:border-b-0"
            >
              <div className="text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
                Question {index + 1}
              </div>
              <label
                htmlFor={id}
                className="mt-1 block text-[14px] font-semibold"
              >
                {item.question}
              </label>
              <p className="mt-1 text-[12.5px] text-muted-foreground">
                Why we ask: {item.reason}
              </p>
              <textarea
                id={id}
                value={answers[index]}
                onChange={(event) =>
                  setAnswers((previous) =>
                    previous.map((answer, at) =>
                      at === index ? event.target.value : answer,
                    ),
                  )
                }
                rows={3}
                disabled={sending}
                className="mt-2 w-full rounded-lg border border-slate-200 bg-card px-2.5 py-2 text-[12.5px]"
              />
            </li>
          );
        })}
      </ol>
      {error ? (
        <p role="alert" className="mt-3 text-[12.5px] text-red-700">
          {error}
        </p>
      ) : null}
      <button
        onClick={send}
        disabled={sending || !complete}
        className="mt-4 cursor-pointer rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {sending ? "Sending…" : "Send answers"}
      </button>
    </div>
  );
}
