/**
 * The Save and Cancel pair under an answer being edited in place.
 *
 * One component for every inline editor on the Brand page, so a questionnaire
 * answer and a Clarification answer are saved and abandoned the same way.
 *
 * Args:
 *   pending: Whether a save is in flight; both buttons wait for it.
 *   onSave: Saves the draft.
 *   onCancel: Abandons the edit.
 */
export function EditActions({
  pending,
  onSave,
  onCancel,
}: {
  pending: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
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
  );
}
