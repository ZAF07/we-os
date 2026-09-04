import { describe, expect, it } from "vitest";

import { formatRange } from "@/lib/calendar";

describe("formatRange", () => {
  it("says how long a campaign runs for, not just when", () => {
    const range = formatRange("2026-09-01", "2026-10-27");

    expect(range).toContain("56 days");
    expect(range).toContain("→");
  });

  it("counts a single-day campaign as zero days between the dates", () => {
    expect(formatRange("2026-09-01", "2026-09-01")).toContain("0 days");
  });

  it("shows the engine's own values rather than 'Invalid Date'", () => {
    expect(formatRange("not-a-date", "2026-10-27")).toBe(
      "not-a-date → 2026-10-27",
    );
    expect(formatRange("", "")).toBe(" → ");
  });
});
