import { describe, expect, it } from "vitest";

import {
  BLANK_ENTRY,
  formatEntries,
  moveEntry,
  parseEntries,
  type Entry,
} from "@/lib/entry-list";

const ENTRIES: Entry[] = [
  { title: "Weekday regulars", description: "buy a drink every morning" },
  { title: "Weekend families", description: "larger orders, price sensitive" },
];

const ANSWER = [
  "Weekday regulars — buy a drink every morning",
  "Weekend families — larger orders, price sensitive",
].join("\n");

describe("parseEntries", () => {
  it("reads one entry per line, split at the first separator", () => {
    expect(parseEntries(ANSWER)).toEqual(ENTRIES);
  });

  it("keeps a title that carries no description", () => {
    expect(parseEntries("Weekday regulars")).toEqual([
      { title: "Weekday regulars", description: "" },
    ]);
  });

  it("keeps a dash inside the description", () => {
    expect(parseEntries("Regulars — buy a drink — every morning")).toEqual([
      { title: "Regulars", description: "buy a drink — every morning" },
    ]);
  });

  it("offers one blank row for an unanswered question, so there is something to type into", () => {
    expect(parseEntries("")).toEqual([BLANK_ENTRY]);
    expect(parseEntries("   \n  ")).toEqual([BLANK_ENTRY]);
  });

  // An answer written before this question collected entries is prose, not
  // entry lines. Splitting it per line turns one paragraph into a dozen junk
  // rows, which is the very "chopped-up prose" this control exists to end — so
  // prose is read as the shape it actually has.
  it("reads a markdown-heading blob as one entry per heading", () => {
    const blob = [
      "### 1. Small agencies",
      "Agencies managing many clients with small teams.",
      "",
      "Typical buyers:",
      "- Agency founders",
      "",
      "### 2. In-house teams",
      "Growing businesses with one or two marketers.",
    ].join("\n");

    expect(parseEntries(blob)).toEqual([
      {
        title: "Small agencies",
        description:
          "Agencies managing many clients with small teams.\nTypical buyers:\n- Agency founders",
      },
      {
        title: "In-house teams",
        description: "Growing businesses with one or two marketers.",
      },
    ]);
  });

  it("reads unstructured prose as a single entry, never one row per line", () => {
    const prose =
      "Busy parents in the suburbs.\nThey want quick weeknight meals.";

    expect(parseEntries(prose)).toEqual([
      {
        title: "Busy parents in the suburbs.",
        description: "They want quick weeknight meals.",
      },
    ]);
  });

  it("still reads a well-formed entry list as one entry per line", () => {
    expect(parseEntries(ANSWER)).toEqual(ENTRIES);
  });
});

describe("formatEntries", () => {
  it("writes one Title — description line per entry, in order", () => {
    expect(formatEntries(ENTRIES)).toBe(ANSWER);
  });

  it("writes a title alone when it has no description", () => {
    expect(formatEntries([{ title: "Regulars", description: " " }])).toBe(
      "Regulars",
    );
  });

  it("drops an entry with no title, since a segment is named or it is nothing", () => {
    expect(formatEntries([...ENTRIES, BLANK_ENTRY])).toBe(ANSWER);
    expect(formatEntries([{ title: " ", description: "orphan detail" }])).toBe(
      "",
    );
  });

  it("round-trips what was parsed", () => {
    expect(formatEntries(parseEntries(ANSWER))).toBe(ANSWER);
  });

  // One entry is one line. A description carrying newlines would otherwise be
  // read back as several entries, shattering the entry it came from — so the
  // newlines are folded away as it is written.
  it("keeps one entry on one line, whatever the description contains", () => {
    const written = formatEntries([
      { title: "Small agencies", description: "Many clients.\nSmall teams." },
    ]);

    expect(written).toBe("Small agencies — Many clients. Small teams.");
    expect(parseEntries(written)).toHaveLength(1);
  });

  it("round-trips a prose answer it had to rescue, without shattering it", () => {
    const blob = [
      "### 1. Small agencies",
      "Many clients, small teams.",
      "Typical buyers:",
      "- Agency founders",
      "### 2. In-house teams",
      "One or two marketers.",
    ].join("\n");

    const rescued = parseEntries(blob);
    expect(parseEntries(formatEntries(rescued))).toHaveLength(rescued.length);
  });
});

describe("moveEntry", () => {
  it("moves an entry, since order carries meaning — most important first", () => {
    expect(moveEntry(ENTRIES, 1, -1)).toEqual([ENTRIES[1], ENTRIES[0]]);
    expect(moveEntry(ENTRIES, 0, 1)).toEqual([ENTRIES[1], ENTRIES[0]]);
  });

  it("leaves the order alone at either end", () => {
    expect(moveEntry(ENTRIES, 0, -1)).toEqual(ENTRIES);
    expect(moveEntry(ENTRIES, 1, 1)).toEqual(ENTRIES);
  });
});
