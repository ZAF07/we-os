/** How much a stat wants to be noticed. */
export type StatTone = "default" | "primary" | "destructive";
import { cn } from "@/lib/utils";

const TONE_CLASSES: Record<StatTone, string> = {
  default: "text-foreground",
  primary: "text-primary",
  destructive: "text-destructive",
};

/**
 * Renders a labeled metric, optionally with a delta line.
 *
 * The tile is a named group, so a screen reader — and a test — can address
 * the metric by its label without colliding with the same words used as a
 * status elsewhere on the page.
 *
 * Args:
 *   label: The metric name.
 *   value: The metric value.
 *   tone: Color tone for the value (default, primary, destructive).
 *   delta: Optional change-vs-prior line rendered under the value.
 *   size: "sm" for the compact bordered chip, "lg" for the large
 *     borderless metric used on the Performance screen.
 *
 * Returns:
 *   The stat element.
 */
export function StatCard({
  label,
  value,
  tone = "default",
  delta,
  size = "sm",
}: {
  label: string;
  value: string;
  tone?: StatTone;
  delta?: string;
  size?: "sm" | "lg";
}) {
  if (size === "lg") {
    return (
      <div role="group" aria-label={label}>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-[22px] font-bold tracking-tight">{value}</div>
        {delta && (
          <div className="text-xs font-semibold text-emerald-700">{delta}</div>
        )}
      </div>
    );
  }
  return (
    <div
      role="group"
      aria-label={label}
      className="min-w-[104px] rounded-[10px] border bg-card px-3.5 py-2"
    >
      <div className="text-[11.5px] text-muted-foreground">{label}</div>
      <div className={cn("text-[17px] font-bold", TONE_CLASSES[tone])}>
        {value}
      </div>
      {delta && (
        <div className="text-[11.5px] font-semibold text-emerald-700">
          {delta}
        </div>
      )}
    </div>
  );
}
