/** The `input_type` whose answer is a list of named entries, one per row. */
export const ENTRY_LIST_TYPE = "entry_list";

/** The separator between an entry's title and its description. */
const SEPARATOR = " — ";

/**
 * Matches the first ` — `, ` – ` or ` - ` on a line, which ends the title.
 *
 * The engine reads these lines back with the same rule — see
 * `_parse_entry` in `agent-harness/src/marketing_os/campaign/goal.py` — so the
 * separators the two accept must stay in step.
 */
const SEPARATOR_RE = /\s+[—–-]\s+/;

export interface Entry {
  title: string;
  description: string;
}

/** An empty row, which an unanswered question starts with. */
export const BLANK_ENTRY: Entry = { title: "", description: "" };

/**
 * Reads an `entry_list` answer as the entries it holds.
 *
 * An answer is plain text — one `Title — description` line per entry — so
 * nothing about storage or rendering has to know a question collects
 * entries. Only the first separator splits, so a dash inside a description
 * survives.
 *
 * Args:
 *   answer: The saved answer text.
 *
 * Returns:
 *   One entry per non-blank line, in the order they were written; a single
 *   blank entry when the answer holds none, so the control has a row to type
 *   into.
 */
export function parseEntries(answer: string): Entry[] {
  const entries = answer
    .split("\n")
    .filter((line) => line.trim() !== "")
    .map(splitEntry);
  return entries.length > 0 ? entries : [{ ...BLANK_ENTRY }];
}

/**
 * Splits one line at its first separator.
 *
 * `String.split` with a limit drops the rest of the line rather than keeping
 * it, so the match is found and the remainder taken whole — a description is
 * free to contain a dash of its own.
 *
 * Args:
 *   line: The entry line, as `Title — description` or a bare title.
 *
 * Returns:
 *   The entry the line describes; the description is empty when the line
 *   carries only a title.
 */
function splitEntry(line: string): Entry {
  const trimmed = line.trim();
  const separator = SEPARATOR_RE.exec(trimmed);
  if (separator === null) return { title: trimmed, description: "" };
  return {
    title: trimmed.slice(0, separator.index).trim(),
    description: trimmed.slice(separator.index + separator[0].length).trim(),
  };
}

/**
 * Writes entries back as the answer text saved against the question.
 *
 * Args:
 *   entries: The entries as edited, in the order they should keep.
 *
 * Returns:
 *   One line per titled entry. An entry with no title is dropped — an entry
 *   is named or it is nothing — and a title with no description is written
 *   on its own.
 */
export function formatEntries(entries: Entry[]): string {
  return entries
    .filter((entry) => entry.title.trim() !== "")
    .map((entry) => {
      const title = entry.title.trim();
      const description = entry.description.trim();
      return description === "" ? title : `${title}${SEPARATOR}${description}`;
    })
    .join("\n");
}

/**
 * Moves one entry up or down, because order carries meaning — the business
 * lists its segments most important first.
 *
 * Args:
 *   entries: The entries as they stand.
 *   index: The entry to move.
 *   offset: How far to move it, negative towards the front.
 *
 * Returns:
 *   The reordered entries, or the same order when the move would run off
 *   either end.
 */
export function moveEntry(
  entries: Entry[],
  index: number,
  offset: number,
): Entry[] {
  const target = index + offset;
  if (target < 0 || target >= entries.length) return entries;
  const moved = [...entries];
  [moved[index], moved[target]] = [moved[target], moved[index]];
  return moved;
}
