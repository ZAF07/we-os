import { cn } from "@/lib/utils";

/**
 * Renders the small uppercase label that opens a public section.
 *
 * Args:
 *   children: The label text.
 *   className: Optional extra classes, e.g. a lighter colour on a dark band.
 */
export function Eyebrow({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "mb-3.5 text-[13px] font-semibold tracking-[0.08em] text-primary uppercase",
        className,
      )}
    >
      {children}
    </p>
  );
}

/**
 * Renders a public section's heading at the Landing's display size.
 *
 * Args:
 *   id: The heading id, so the section can be labelled by it.
 *   children: The heading text.
 *   className: Optional extra classes.
 */
export function SectionHeading({
  id,
  children,
  className,
}: {
  id?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h2
      id={id}
      className={cn(
        "text-[clamp(30px,3.6vw,44px)] leading-[1.1] font-bold tracking-[-0.03em]",
        className,
      )}
    >
      {children}
    </h2>
  );
}
