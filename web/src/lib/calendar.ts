/**
 * Renders a campaign's timeframe as one readable line.
 *
 * Args:
 *   start: The ISO start date.
 *   end: The ISO end date.
 *
 * Returns:
 *   The range and how long it runs for, or the raw dates when either is not a
 *   date the browser understands — showing what the engine actually holds beats
 *   showing "Invalid Date".
 */
export function formatRange(start: string, end: string): string {
  const from = new Date(start);
  const to = new Date(end);
  if (Number.isNaN(from.valueOf()) || Number.isNaN(to.valueOf())) {
    return `${start} → ${end}`;
  }
  const days = Math.round((to.valueOf() - from.valueOf()) / 86_400_000);
  const shown: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${from.toLocaleDateString(undefined, shown)} → ${to.toLocaleDateString(undefined, shown)} · ${days} days`;
}
