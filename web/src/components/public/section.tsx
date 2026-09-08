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
 *   as: The heading level: `h2` within a page, `h1` when the section is the
 *     page.
 *   children: The heading text.
 *   className: Optional extra classes.
 */
export function SectionHeading({
  id,
  as: Heading = "h2",
  children,
  className,
}: {
  id?: string;
  as?: "h1" | "h2";
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Heading
      id={id}
      className={cn(
        "text-[clamp(30px,3.6vw,44px)] leading-[1.1] font-bold tracking-[-0.03em]",
        className,
      )}
    >
      {children}
    </Heading>
  );
}

/**
 * Renders the centred column every public section lays out in.
 *
 * Args:
 *   children: The section's content.
 *   className: Optional extra classes, usually vertical padding.
 */
export function Container({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto max-w-[1180px] px-5 md:px-10", className)}>
      {children}
    </div>
  );
}
