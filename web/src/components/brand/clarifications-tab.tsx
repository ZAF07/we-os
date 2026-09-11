"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { Clarification } from "@/lib/engine";
import { stageTitle } from "@/lib/workspace";

/**
 * Lists every fact a specialist asked the business for, and lets each answer
 * be corrected in place.
 *
 * A Clarification is part of the Brand DNA (ADR-0028), so this is the same
 * kind of editor the questionnaire tabs are: what is shown is what was
 * answered, and changing it is changing the answer. Each item names the
 * question, why it was asked, and which stage of which campaign asked, so the
 * owner can tell what the system knows about them beyond the questionnaire.
 * An edit re-runs nothing.
 *
 * Args:
 *   clarifications: The tenant's Clarifications, in the order they were answered.
 *   save: Saves one corrected answer; resolves with the Clarification as saved.
 */
export function ClarificationsTab({
  clarifications,
  save,
}: {
  clarifications: Clarification[];
  save: (clarificationId: string, answer: string) => Promise<Clarification>;
}) {
  const router = useRouter();
  const [items, setItems] = useState(clarifications);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startSaving] = useTransition();

  const submit = (clarificationId: string) => {
    const answer = draft.trim();
    if (answer === "") {
      setError(
        "An answer cannot be blank. Type an answer, or Cancel to keep the one you gave.",
      );
      return;
    }
    setError(null);
    startSaving(async () => {
      try {
        const saved = await save(clarificationId, answer);
        setItems((previous) =>
          previous.map((item) => (item.id === saved.id ? saved : item)),
        );
        setEditing(null);
        router.refresh();
      } catch {
        setError("Could not save that answer. Try again.");
      }
    });
  };

  if (items.length === 0) {
    return (
      <p className="rounded-xl border bg-card px-[18px] py-[15px] text-[13.5px] text-slate-700">
        No Clarifications yet. When a specialist asks you during a campaign for
        a fact your Brand DNA does not carry, your answer is saved here, and
        every later campaign reads it.
      </p>
    );
  }

  return (
    <>
      {error && (
        <p
          role="alert"
          className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
        >
          {error}
        </p>
      )}
      <ol aria-label="Clarifications" className="flex flex-col gap-3">
        {items.map((item) => (
          <ClarificationCard
            key={item.id}
            clarification={item}
            editing={editing === item.id}
            draft={draft}
            pending={pending}
            onEdit={() => {
              setEditing(item.id);
              setDraft(item.answer);
              setError(null);
            }}
            onDraft={setDraft}
            onCancel={() => {
              setEditing(null);
              setError(null);
            }}
            onSave={() => submit(item.id)}
          />
        ))}
      </ol>
    </>
  );
}

/**
 * Renders one Clarification: the question, why and where it was asked, and
 * the answer, editable in place.
 *
 * Args:
 *   clarification: The question, its answer, and where it was asked.
 *   editing: Whether this card is the one being edited.
 *   draft: The text being typed, when editing.
 *   pending: Whether a save is in flight.
 *   onEdit: Starts editing this answer.
 *   onDraft: Records a keystroke.
 *   onCancel: Abandons the edit.
 *   onSave: Saves the draft.
 */
function ClarificationCard({
  clarification,
  editing,
  draft,
  pending,
  onEdit,
  onDraft,
  onCancel,
  onSave,
}: {
  clarification: Clarification;
  editing: boolean;
  draft: string;
  pending: boolean;
  onEdit: () => void;
  onDraft: (value: string) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  const inputId = `clarification-${clarification.id}`;
  return (
    <li className="rounded-xl border bg-card px-[18px] py-[15px]">
      {editing ? (
        <label htmlFor={inputId} className="block text-[13.5px] font-bold">
          {clarification.question}
        </label>
      ) : (
        <div className="text-[13.5px] font-bold">{clarification.question}</div>
      )}
      <div className="mt-0.5 text-[11.5px] text-muted-foreground">
        Why it was asked: {clarification.reason}
      </div>
      <div className="mt-0.5 text-[11.5px] text-muted-foreground">
        Asked by {stageTitle(clarification.stage)} for campaign{" "}
        {clarification.slug}
      </div>

      {editing ? (
        <div className="mt-2.5">
          <textarea
            id={inputId}
            value={draft}
            onChange={(event) => onDraft(event.target.value)}
            rows={3}
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
            {clarification.answer}
          </div>
          <button
            onClick={onEdit}
            aria-label={`Edit answer: ${clarification.question}`}
            className="shrink-0 cursor-pointer rounded-md px-2 py-1 text-[12.5px] font-semibold text-primary hover:bg-indigo-50"
          >
            Edit
          </button>
        </div>
      )}
    </li>
  );
}
