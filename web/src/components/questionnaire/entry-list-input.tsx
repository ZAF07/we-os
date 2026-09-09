"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  BLANK_ENTRY,
  formatEntries,
  moveEntry,
  parseEntries,
  type Entry,
} from "@/lib/entry-list";

/**
 * Renders an `entry_list` answer as repeatable title-and-description rows.
 *
 * The control keys off the question's `input_type` and knows nothing about
 * which question it is serving (ADR-0018), so any question collecting named
 * entries gets it. Order carries meaning — the business lists its groups most
 * important first — so rows can be moved as well as added and removed.
 *
 * The answer stays plain text: rows are read from and written back to the
 * `Title — description` lines the answer already holds, which is what lets
 * storage, rendering and the Brand DNA markdown stay unchanged. The rows
 * themselves are held here rather than re-read from that text on every
 * keystroke, so a row being filled in — a description typed before its name —
 * stays on screen even though it is not yet a saveable entry.
 *
 * Args:
 *   label: The question as it is asked, which names the group of rows —
 *     a repeatable control is a group, not one box a `<label>` can point at.
 *   value: The answer text as saved, which seeds the rows.
 *   titlePlaceholder: The hint shown in an empty title box.
 *   descriptionPlaceholder: The hint shown in an empty description box.
 *   onChange: Called with the rewritten answer text.
 *
 * Returns:
 *   The entry rows and their Add control.
 */
export function EntryListInput({
  label,
  value,
  titlePlaceholder,
  descriptionPlaceholder,
  onChange,
}: {
  label: string;
  value: string;
  titlePlaceholder: string;
  descriptionPlaceholder: string;
  onChange: (value: string) => void;
}) {
  const [entries, setEntries] = useState(() => parseEntries(value));

  const write = (next: Entry[]) => {
    setEntries(next);
    onChange(formatEntries(next));
  };

  const edit =
    (index: number, field: "title" | "description") =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      write(
        entries.map((entry, at) =>
          at === index ? { ...entry, [field]: event.target.value } : entry,
        ),
      );

  return (
    <div role="group" aria-label={label} className="flex flex-col gap-2.5">
      {entries.map((entry, index) => (
        <div
          key={index}
          className="flex flex-col gap-1.5 rounded-lg border bg-card px-3 py-2.5"
        >
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold text-muted-foreground">
              {index + 1}
            </span>
            <Input
              value={entry.title}
              aria-label={`Name of entry ${index + 1}`}
              placeholder={titlePlaceholder}
              onChange={edit(index, "title")}
            />
            <button
              type="button"
              aria-label={`Move entry ${index + 1} up`}
              disabled={index === 0}
              onClick={() => write(moveEntry(entries, index, -1))}
              className="cursor-pointer rounded-md border px-2 py-1 text-[12px] font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ↑
            </button>
            <button
              type="button"
              aria-label={`Move entry ${index + 1} down`}
              disabled={index === entries.length - 1}
              onClick={() => write(moveEntry(entries, index, 1))}
              className="cursor-pointer rounded-md border px-2 py-1 text-[12px] font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ↓
            </button>
            <button
              type="button"
              aria-label={`Remove entry ${index + 1}`}
              onClick={() => write(entries.filter((_, at) => at !== index))}
              className="cursor-pointer rounded-md border px-2 py-1 text-[12px] font-semibold text-red-700 hover:bg-red-50"
            >
              Remove
            </button>
          </div>
          <Textarea
            value={entry.description}
            aria-label={`What defines entry ${index + 1}`}
            placeholder={descriptionPlaceholder}
            rows={2}
            onChange={edit(index, "description")}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => write([...entries, { ...BLANK_ENTRY }])}
        className="cursor-pointer self-start rounded-lg border bg-card px-3 py-1.5 text-[12.5px] font-semibold text-primary hover:bg-indigo-50"
      >
        + Add another
      </button>
    </div>
  );
}
