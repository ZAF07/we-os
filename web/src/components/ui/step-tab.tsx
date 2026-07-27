import { cn } from "@/lib/utils";

/**
 * Renders one numbered step chip in a horizontal progress row, as a
 * button when interactive and a plain element otherwise. The dot
 * reflects completion, the label and underline reflect selection —
 * independently, matching the prototype's stepper.
 *
 * Args:
 *   mark: The number shown in the dot (replaced by a check when done).
 *   label: The step name.
 *   done: Whether the step is completed.
 *   active: Whether the step is the selected/current one.
 *   onClick: Optional handler; when present the chip is a button.
 *
 * Returns:
 *   The step chip element.
 */
export function StepTab({
  mark,
  label,
  done,
  active,
  onClick,
}: {
  mark: string;
  label: string;
  done: boolean;
  active: boolean;
  onClick?: () => void;
}) {
  const className = cn(
    "flex items-center gap-[7px] border-b-2 px-2.5 pt-2 pb-2.5 whitespace-nowrap",
    active ? "border-primary" : "border-transparent",
    onClick && "cursor-pointer hover:bg-slate-50",
  );
  const content = (
    <>
      <span
        className={cn(
          "flex size-4 items-center justify-center rounded-full border-[1.5px] text-[9.5px] font-bold",
          done
            ? "border-emerald-500 bg-emerald-500 text-white"
            : active
              ? "border-primary bg-primary text-white"
              : "border-slate-300 bg-card text-slate-400",
        )}
      >
        {done ? "✓" : mark}
      </span>
      <span
        className={cn(
          "text-[12.5px]",
          active
            ? "font-bold text-foreground"
            : done
              ? "font-medium text-slate-700"
              : "font-medium text-slate-400",
        )}
      >
        {label}
      </span>
    </>
  );
  if (onClick) {
    return (
      <button onClick={onClick} className={className}>
        {content}
      </button>
    );
  }
  return (
    <div aria-current={active ? "step" : undefined} className={className}>
      {content}
    </div>
  );
}
