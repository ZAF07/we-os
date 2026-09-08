import { describe, expect, it } from "vitest";

import {
  headingNamesPart,
  isBullet,
  kpiTier,
  planPart,
  plainText,
  toSections,
  withoutTierLabel,
} from "@/lib/deliverable";

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

  it("does not mistake a # inside a code fence for a heading", () => {
    const sections = toSections(
      [
        "## Channel mix",
        "- Meta: 60%",
        "```",
        "# this is sample copy, not a section",
        "```",
        "## KPI targets",
        "Business: 40 memberships",
      ].join("\n"),
    );

    expect(sections.map((section) => section.heading)).toEqual([
      "Channel mix",
      "KPI targets",
    ]);
    expect(sections[0].lines).toContain("# this is sample copy, not a section");
  });

  it("handles a fence left unclosed rather than swallowing the rest", () => {
    const sections = toSections("## Channels\n```\nunclosed");

    expect(sections).toHaveLength(1);
    expect(sections[0].heading).toBe("Channels");
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

describe("planPart", () => {
  it("recognises the four parts a performance plan is required to have", () => {
    expect(planPart("Channel mix")).toBe("channels");
    expect(planPart("Spend allocation")).toBe("spend");
    expect(planPart("Placements")).toBe("placements");
    expect(planPart("KPI targets")).toBe("kpis");
  });

  it("recognises the wordings a specialist plausibly writes instead", () => {
    expect(planPart("Channel selection & rationale")).toBe("channels");
    expect(planPart("2. Budget allocation")).toBe("spend");
    expect(planPart("Placements and format specs")).toBe("placements");
    expect(planPart("KPI plan across all three tiers")).toBe("kpis");
    expect(planPart("Success metrics")).toBe("kpis");
  });

  it("leaves a heading it does not recognise unidentified", () => {
    expect(planPart("Notes")).toBeNull();
    expect(planPart("Optimization guidance")).toBeNull();
    expect(planPart("")).toBeNull();
  });

  it("reads budget as spend even though both words appear in one heading", () => {
    expect(planPart("Channel mix and budget split")).toBe("spend");
  });
});

describe("kpiTier", () => {
  it("reads which tier a KPI line belongs to", () => {
    expect(kpiTier("- **Business**: 40 memberships")).toBe("Business");
    expect(kpiTier("Marketing KPI: 2.5% CTR")).toBe("Marketing");
    expect(kpiTier("- Creative — hook rate above 30%")).toBe("Creative");
  });

  it("has no tier for a line that names none", () => {
    expect(kpiTier("Measured weekly.")).toBeNull();
  });
});

describe("headingNamesPart", () => {
  it("is true when the heading already carries the part's own words", () => {
    expect(headingNamesPart("Channel mix", "channels")).toBe(true);
    expect(headingNamesPart("Placements and format specs", "placements")).toBe(
      true,
    );
    expect(headingNamesPart("KPI targets", "kpis")).toBe(true);
  });

  it("is false when the heading matched on a different word", () => {
    expect(headingNamesPart("Budget allocation", "spend")).toBe(false);
    expect(headingNamesPart("Media split", "channels")).toBe(false);
    expect(headingNamesPart("Success metrics", "kpis")).toBe(false);
  });
});

describe("withoutTierLabel", () => {
  it("drops the tier name a card already displays above the line", () => {
    expect(withoutTierLabel("- **Business**: 40 memberships", "Business")).toBe(
      "40 memberships",
    );
    expect(withoutTierLabel("Marketing KPI: 2.5% CTR", "Marketing")).toBe(
      "2.5% CTR",
    );
    expect(
      withoutTierLabel("- Creative — hook rate above 30%", "Creative"),
    ).toBe("hook rate above 30%");
  });

  it("keeps the line whole when the tier is not a label on the front", () => {
    expect(
      withoutTierLabel("Every target is a business outcome", "Business"),
    ).toBe("Every target is a business outcome");
  });
});

describe("reading a whole performance plan", () => {
  const SEEDED_PLAN = [
    "# Performance Plan — Spring memberships",
    "",
    "## Channel mix",
    "- Meta: the segment's main discovery surface.",
    "- TikTok: reaches the under-30 half of the segment.",
    "",
    "## Budget allocation",
    "- Meta: 60% (£3,000)",
    "- TikTok: 40% (£2,000)",
    "",
    "## Placements and format specs",
    "- Meta Feed — 1:1, 1080x1080, 125 char primary text",
    "- TikTok In-Feed — 9:16, 1080x1920, 9s max",
    "",
    "## KPI targets",
    "- **Business**: 40 new memberships",
    "- **Marketing**: 2.5% CTR",
    "- **Creative**: hook rate above 30%",
  ].join("\n");

  it("identifies each of the four parts a seeded plan carries", () => {
    const parts = toSections(SEEDED_PLAN).map((section) =>
      planPart(section.heading),
    );

    expect(parts).toEqual([null, "channels", "spend", "placements", "kpis"]);
  });

  it("groups the KPI section's lines under all three tiers", () => {
    const kpis = toSections(SEEDED_PLAN).find(
      (section) => planPart(section.heading) === "kpis",
    );

    expect(kpis?.lines.map(kpiTier)).toEqual([
      "Business",
      "Marketing",
      "Creative",
    ]);
  });

  it("identifies nothing in a plan whose headings match none of the parts", () => {
    const sections = toSections(
      [
        "## Notes",
        "Written up after the call.",
        "## Open questions",
        "None.",
      ].join("\n"),
    );

    expect(sections.map((section) => planPart(section.heading))).toEqual([
      null,
      null,
    ]);
    expect(sections[0].lines).toEqual(["Written up after the call."]);
  });
});
