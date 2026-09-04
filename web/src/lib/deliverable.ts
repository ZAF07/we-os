export interface DeliverableSection {
  heading: string;
  lines: string[];
}

/**
 * Splits a deliverable's markdown into the sections a screen can lay out.
 *
 * Specialists write markdown, and the headings they choose are the structure of
 * their own decision — a Performance Plan's channel mix, its spend allocation,
 * its placements, its KPI tiers. Reading those headings is what lets a screen
 * present the plan as sections rather than as a wall of raw text with `##` and
 * `**` still in it.
 *
 * Deliberately shallow: it finds headings and the lines beneath them, and does
 * not try to be a markdown renderer. A specialist is free to write whatever it
 * judges the stage needs, so a screen that assumed a fixed shape would break the
 * first time one of them wrote something sensible but different.
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
