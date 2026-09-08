export interface DeliverableSection {
  heading: string;
  lines: string[];
}

/**
 * Splits a deliverable's markdown into the sections a screen can lay out.
 *
 * Specialists write markdown, and the headings they choose are the structure of
 * their own decision — a Performance Plan's channel mix, its spend allocation,
 * its placements, its KPI tiers. Splitting on those headings is what lets a
 * screen present the plan as sections rather than as a wall of raw text with
 * `##` and `**` still in it, and `planPart` below reads the heading's words so
 * the screen can say which of the four parts a section is.
 *
 * That identification is a **reader's** convenience, not a check. Whether a plan
 * has all four parts is settled upstream, by `guardrails/performance-plan.md`
 * and the reviewer that scores every plan against it, so a specialist wording a
 * heading unusually costs a section its special treatment and nothing more — it
 * renders plainly, and no governance failure passes unnoticed. Structured output
 * from the engine would remove even that cosmetic risk; it is deferred until
 * Performance is a priority. See
 * `.scratch/saas-foundation/issues/archive/16-*.md` for the reasoning.
 *
 * Deliberately shallow otherwise: it finds headings and the lines beneath them,
 * and does not try to be a markdown renderer.
 *
 * Args:
 *   markdown: The deliverable as the specialist saved it.
 *
 * Returns:
 *   One section per heading, in document order. Text before the first heading
 *   becomes a leading section with an empty heading, so nothing is dropped.
 */
export function toSections(markdown: string): DeliverableSection[] {
  const sections: DeliverableSection[] = [];
  let current: DeliverableSection = { heading: "", lines: [] };
  let insideFence = false;

  const keep = (section: DeliverableSection): void => {
    if (section.heading !== "" || section.lines.length > 0) {
      sections.push(section);
    }
  };

  for (const raw of markdown.split("\n")) {
    if (/^\s{0,3}(```|~~~)/.test(raw)) {
      insideFence = !insideFence;
      current.lines.push(raw.trimEnd());
      continue;
    }

    const heading = insideFence ? null : raw.match(/^\s{0,3}#{1,6}\s+(.*)$/);
    if (heading) {
      keep(current);
      current = { heading: heading[1].trim(), lines: [] };
      continue;
    }

    if (raw.trim() !== "") current.lines.push(raw.trimEnd());
  }

  keep(current);
  return sections;
}

/**
 * Strips the markdown emphasis a plain-text renderer would otherwise show.
 *
 * The screen lays sections out itself, so what it needs from each line is the
 * words — leaving `**bold**` and list bullets in place would show the markup
 * rather than the decision.
 *
 * Args:
 *   line: One line of a deliverable.
 *
 * Returns:
 *   The line's text, without emphasis markers or a leading bullet.
 */
export function plainText(line: string): string {
  return line
    .replace(/^\s*[-*+]\s+/, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .trim();
}

/**
 * Reports whether a line was written as a list item.
 *
 * Args:
 *   line: One line of a deliverable.
 *
 * Returns:
 *   Whether the specialist wrote it as a bullet, so the screen can lay it out
 *   as one rather than as a paragraph.
 */
export function isBullet(line: string): boolean {
  return /^\s*[-*+]\s+/.test(line);
}

/** Which of a Performance Plan's four required parts a section holds. */
export type PlanPart = "channels" | "spend" | "placements" | "kpis";

/** One of the three KPI tiers every campaign is required to define. */
export type KpiTierName = "Business" | "Marketing" | "Creative";

const PART_PATTERNS: ReadonlyArray<[PlanPart, RegExp]> = [
  ["spend", /\b(spend|budget|allocation|investment)\b/i],
  ["kpis", /\b(kpi|kpis|success metric|success metrics|target|targets)\b/i],
  ["placements", /\b(placement|placements|format|formats|spec|specs)\b/i],
  ["channels", /\b(channel|channels|media mix)\b/i],
];

const TIER_PATTERNS: ReadonlyArray<[KpiTierName, RegExp]> = [
  ["Business", /\bbusiness\b/i],
  ["Marketing", /\bmarketing\b/i],
  ["Creative", /\bcreative\b/i],
];

/**
 * Identifies which part of a Performance Plan a heading introduces.
 *
 * The plan's four required parts — the channel mix, the per-channel spend
 * allocation, the placements with their format specs, and the KPI targets
 * across all three tiers — are required by `guardrails/performance-plan.md`,
 * not by the specialist's choice of words. Matching the words is how the screen
 * can say *which* part it is showing rather than laying every section out
 * identically.
 *
 * Ordered so the more specific word wins where two appear: a heading reading
 * "Channel mix and budget split" is the spend allocation, since that is the
 * decision its lines carry.
 *
 * Args:
 *   heading: A section heading, as the specialist wrote it.
 *
 * Returns:
 *   The part the heading names, or null when it names none — an unrecognised
 *   heading is a section the screen renders plainly, not an error.
 */
export function planPart(heading: string): PlanPart | null {
  for (const [part, pattern] of PART_PATTERNS) {
    if (pattern.test(heading)) return part;
  }
  return null;
}

/**
 * Reads which KPI tier a line reports on.
 *
 * `.claude/rules/operating-principles.md` requires all three tiers — Business,
 * Marketing, Creative — so a KPI section's lines are grouped by the tier they
 * name rather than listed flat.
 *
 * Args:
 *   line: One line of a KPI section.
 *
 * Returns:
 *   The tier the line names, or null when it names none.
 */
export function kpiTier(line: string): KpiTierName | null {
  for (const [tier, pattern] of TIER_PATTERNS) {
    if (pattern.test(line)) return tier;
  }
  return null;
}

/**
 * Drops the tier name from the front of a KPI line.
 *
 * The screen groups KPI lines into a card per tier, so a line still reading
 * "Business: 40 memberships" under a card headed "Business" says the same thing
 * twice. Only a leading label is removed — a line that merely mentions the word
 * keeps every word the specialist wrote.
 *
 * Args:
 *   line: One line of a KPI section.
 *   tier: The tier whose card the line is being shown under.
 *
 * Returns:
 *   The line's text without its leading tier label, and without the separator
 *   and any "KPI" that followed it.
 */
export function withoutTierLabel(line: string, tier: KpiTierName): string {
  const label = new RegExp(`^${tier}(\\s+KPIs?)?\\s*[:\\-–—]\\s*`, "i");
  return plainText(line).replace(label, "").trim();
}
