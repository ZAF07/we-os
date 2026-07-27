import { cn } from "@/lib/utils";

/**
 * Renders the app's standard white, bordered, rounded panel.
 *
 * Args:
 *   className: Optional extra classes (e.g. padding for headerless cards).
 *   children: Panel content.
 *
 * Returns:
 *   The card section element.
 */
export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn("overflow-hidden rounded-xl border bg-card", className)}
    >
      {children}
    </section>
  );
}

/**
 * Renders a card's title row with an optional trailing action.
 *
 * Args:
 *   title: The bold card title.
 *   action: Optional right-aligned element (count, link, toggle).
 *   className: Optional extra classes.
 *
 * Returns:
 *   The header element.
 */
export function CardHeader({
  title,
  action,
  className,
}: {
  title: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between border-b px-[18px] py-3.5",
        className,
      )}
    >
      <div className="text-sm font-bold">{title}</div>
      {action}
    </div>
  );
}
