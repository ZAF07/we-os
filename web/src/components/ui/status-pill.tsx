import { statusPillClasses, type Status } from "@/lib/status";
import { cn } from "@/lib/utils";

/**
 * Renders a status label in the canonical taxonomy colors.
 *
 * Args:
 *   status: One of the nine canonical statuses.
 *   className: Optional extra classes (e.g. a smaller text size).
 *
 * Returns:
 *   The status pill element.
 */
export function StatusPill({
  status,
  className,
}: {
  status: Status;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "rounded-md px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
        statusPillClasses(status),
        className,
      )}
    >
      {status}
    </span>
  );
}
