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
