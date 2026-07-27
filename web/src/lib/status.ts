export const STATUSES = [
  "Draft",
  "Needs input",
  "In progress",
  "Ready for review",
  "Approved",
  "Scheduled",
  "Published",
  "Needs attention",
  "Not started",
] as const;

export type Status = (typeof STATUSES)[number];

const STATUS_PILL_CLASSES: Record<Status, string> = {
  Draft: "bg-slate-100 text-slate-600",
  "Needs input": "bg-amber-100 text-amber-700",
  "In progress": "bg-indigo-100 text-indigo-700",
  "Ready for review": "bg-violet-100 text-violet-700",
  Approved: "bg-emerald-100 text-emerald-700",
  Scheduled: "bg-sky-100 text-sky-700",
  Published: "bg-slate-100 text-slate-700",
  "Needs attention": "bg-red-100 text-red-700",
  "Not started": "bg-slate-50 text-slate-400",
};

const STATUS_EDGE_CLASSES: Record<Status, string> = {
  Draft: "border-slate-600",
  "Needs input": "border-amber-700",
  "In progress": "border-indigo-700",
  "Ready for review": "border-violet-700",
  Approved: "border-emerald-700",
  Scheduled: "border-sky-700",
  Published: "border-slate-700",
  "Needs attention": "border-red-700",
  "Not started": "border-slate-400",
};

const STATUS_DOT_CLASSES: Record<Status, string> = {
  Draft: "bg-slate-400",
  "Needs input": "bg-amber-500",
  "In progress": "bg-indigo-600",
  "Ready for review": "bg-violet-500",
  Approved: "bg-emerald-500",
  Scheduled: "bg-sky-500",
  Published: "bg-slate-500",
  "Needs attention": "bg-red-500",
  "Not started": "bg-slate-300",
};

/**
 * Returns the background/foreground classes for a status pill.
 *
 * Args:
 *   status: One of the nine canonical statuses.
 *
 * Returns:
 *   Tailwind classes for the pill's background and text colors.
 */
export function statusPillClasses(status: Status): string {
  return STATUS_PILL_CLASSES[status];
}

/**
 * Returns the border color class matching a status's foreground color.
 *
 * Args:
 *   status: One of the nine canonical statuses.
 *
 * Returns:
 *   A Tailwind border-color class, used for status-colored edges.
 */
export function statusEdgeClass(status: Status): string {
  return STATUS_EDGE_CLASSES[status];
}

/**
 * Returns the background class for a small status indicator dot.
 *
 * Args:
 *   status: One of the nine canonical statuses.
 *
 * Returns:
 *   A Tailwind background-color class for the dot.
 */
export function statusDotClass(status: Status): string {
  return STATUS_DOT_CLASSES[status];
}
