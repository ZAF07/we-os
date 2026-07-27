import type { StatTone } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const TONE_CLASSES: Record<StatTone, string> = {
  default: "text-foreground",
  primary: "text-primary",
  destructive: "text-destructive",
};

/**
 * Renders a labeled metric, optionally with a delta line.
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
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-[22px] font-bold tracking-tight">{value}</div>
        {delta && (
          <div className="text-xs font-semibold text-emerald-700">{delta}</div>
        )}
      </div>
    );
  }
  return (
    <div className="min-w-[104px] rounded-[10px] border bg-card px-3.5 py-2">
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
