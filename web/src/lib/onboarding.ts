import {
  BRAND_SECTIONS,
  type BrandEntry,
  type BrandSection,
} from "@/lib/mock-data";

export interface OnboardingSegment {
  name: string;
  desc: string;
}

export interface OnboardingData {
  companyName: string;
  companyDescription: string;
  industry: string;
  products: string;
  website: string;
  segments: OnboardingSegment[];
  problems: string;
  valueProp: string;
  promise: string;
  differentiators: string;
  claims: string;
  competitors: string;
  avoid: string;
  personality: string;
  tone: string;
  writingStyle: string;
  prohibitedTerms: string;
  restricted: string;
  disclaimers: string;
}

const LINE_SEPARATOR = /\s+[—–-]\s+/;

/**
 * Parses a multi-line "Name — detail" text block into brand entries.
 *
 * Args:
 *   text: One entry per line; an em/en dash or hyphen separates the
 *     entry name from its detail.
 *   warn: Whether the entries render as restricted-language warnings.
 *
 * Returns:
 *   One brand entry per non-empty line.
 */
export function parseEntries(text: string, warn?: boolean): BrandEntry[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(LINE_SEPARATOR);
      return {
        k: parts[0].trim(),
        v: parts.slice(1).join(" — ").trim(),
        warn,
      };
    });
}

/**
 * Returns the audience segment names campaigns can target.
 *
 * Args:
 *   data: Completed onboarding entries, or null before onboarding.
 *
 * Returns:
 *   Onboarded segment names when available, otherwise the fixture
 *   Audience segments with their rank prefix stripped.
 */
export function audienceSegmentOptions(data: OnboardingData | null): string[] {
  if (data) {
    const names = data.segments
      .map((segment) => segment.name.trim())
      .filter(Boolean);
    if (names.length) return names;
  }
  const fixture = BRAND_SECTIONS.find(
    (section) => section.name === "Audience segments",
  );
  return (fixture?.entries ?? []).map((entry) =>
    entry.k.replace(/^\d+\s*·\s*/, ""),
  );
}

/**
 * Builds the Brand screen sections, overlaying completed onboarding
 * data on the fixture sections.
 *
 * Args:
 *   data: Completed onboarding entries, or null before onboarding.
 *
 * Returns:
 *   The nine brand sections; sections the wizard covers are replaced
 *   with the operator's entries and marked verified "Just now".
 */
export function brandSectionsWithOnboarding(
  data: OnboardingData | null,
): BrandSection[] {
  if (!data) return BRAND_SECTIONS;

  const overrides = new Map<string, Pick<BrandSection, "desc" | "entries">>();

  overrides.set("Positioning", {
    desc: `The single idea ${data.companyName} owns and the frame every campaign starts from.`,
    entries: [
      { k: "Core value proposition", v: data.valueProp },
      { k: "Customer promise", v: data.promise },
      { k: "Key differentiators", v: data.differentiators },
      ...(data.avoid ? [{ k: "Avoid", v: data.avoid }] : []),
    ],
  });

  const products = parseEntries(data.products);
  if (products.length) {
    overrides.set("Products & services", {
      desc: "What we sell, in the language we sell it in.",
      entries: products,
    });
  }

  overrides.set("Audience segments", {
    desc: "Who we speak to, ranked by strategic priority.",
    entries: [
      ...data.segments
        .filter((segment) => segment.name.trim())
        .map((segment, index) => ({
          k: `${index + 1} · ${segment.name}`,
          v: segment.desc,
        })),
      ...(data.problems
        ? [{ k: "Problems & pain points", v: data.problems }]
        : []),
    ],
  });

  overrides.set("Voice & tone", {
    desc: `How ${data.companyName} sounds, everywhere.`,
    entries: [
      { k: "Personality", v: data.personality },
      { k: "Tone of voice", v: data.tone },
      ...(data.writingStyle
        ? [{ k: "Writing style", v: data.writingStyle }]
        : []),
    ],
  });

  const claims = parseEntries(data.claims);
  if (claims.length) {
    overrides.set("Claims & evidence", {
      desc: "Every claim we make in public, with what backs it.",
      entries: claims,
    });
  }

  const restricted = parseEntries(
    [data.restricted, data.prohibitedTerms].filter(Boolean).join("\n"),
    true,
  );
  if (restricted.length) {
    overrides.set("Restricted language", {
      desc: "Words and claims that must never appear in published assets.",
      entries: [
        ...restricted,
        ...(data.disclaimers
          ? [{ k: "Required disclaimers", v: data.disclaimers }]
          : []),
      ],
    });
  }

  const competitors = parseEntries(data.competitors);
  if (competitors.length) {
    overrides.set("Competitors", {
      desc: "Who we are compared against and how we differ.",
      entries: competitors,
    });
  }

  return BRAND_SECTIONS.map((section) => {
    const override = overrides.get(section.name);
    if (!override) return section;
    return { ...section, ...override, verified: "Just now" };
  });
}
