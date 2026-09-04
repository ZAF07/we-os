import { describe, expect, it } from "vitest";

import { isBullet, plainText, toSections } from "@/lib/deliverable";

describe("toSections", () => {
  it("splits a plan into the sections its headings define", () => {
    const sections = toSections(
      [
        "# Performance Plan",
        "",
        "## Channel mix",
        "- Meta: 60% of spend",
        "- TikTok: 40% of spend",
        "",
        "## KPI targets",
        "Business: 40 memberships",
      ].join("\n"),
    );

    expect(sections.map((section) => section.heading)).toEqual([
      "Performance Plan",
      "Channel mix",
      "KPI targets",
    ]);
    expect(sections[1].lines).toEqual([
      "- Meta: 60% of spend",
      "- TikTok: 40% of spend",
    ]);
  });

  it("keeps text written before any heading rather than dropping it", () => {
    const sections = toSections("A preamble.\n\n## Channels\nMeta.");

    expect(sections[0].heading).toBe("");
    expect(sections[0].lines).toEqual(["A preamble."]);
  });

  it("reads headings at any depth, since specialists choose their own", () => {
    const sections = toSections("### Placements\nMeta feed 1:1");

    expect(sections[0].heading).toBe("Placements");
  });

  it("has nothing to show for an empty deliverable", () => {
    expect(toSections("")).toEqual([]);
    expect(toSections("\n\n  \n")).toEqual([]);
  });
});

describe("plainText", () => {
  it("removes the markup a plain renderer would otherwise display", () => {
    expect(plainText("- **Meta**: 60% of spend")).toBe("Meta: 60% of spend");
    expect(plainText("* `research.md` written")).toBe("research.md written");
  });

  it("leaves ordinary prose alone", () => {
    expect(plainText("Lead with the coached first session.")).toBe(
      "Lead with the coached first session.",
    );
  });
});

describe("isBullet", () => {
  it("tells a list item from a paragraph", () => {
    expect(isBullet("- Meta")).toBe(true);
    expect(isBullet("  * TikTok")).toBe(true);
    expect(isBullet("Business: 40 memberships")).toBe(false);
  });
});
