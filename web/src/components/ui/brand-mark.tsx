import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Renders the We-OS logo mark and wordmark.
 *
 * One component for every place the name appears — the app shell, the public
 * top bar and the footer — so the product has one name and one mark wherever
 * a person sees it.
 *
 * Args:
 *   size: `"default"` for the shell and the footer, `"large"` for the public
 *     top bar.
 *   className: Optional extra classes.
 *   props: Anything else a span accepts, so a parent can label or slot it.
 *
 * Returns:
 *   The mark and wordmark, inline.
 */
export function BrandMark({
  size = "default",
  className,
  ...props
}: React.ComponentProps<"span"> & { size?: "default" | "large" }) {
  const large = size === "large";
  return (
    <span
      className={cn(
        "inline-flex items-center",
        large ? "gap-2.5" : "gap-[9px]",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          "flex items-center justify-center bg-gradient-to-br from-indigo-600 to-indigo-500 font-bold text-white",
          large
            ? "size-[30px] rounded-[9px] text-sm"
            : "size-6 rounded-[7px] text-[13px]",
        )}
      >
        W
      </span>
      <span
        className={cn(
          "font-bold tracking-tight",
          large ? "text-[17px]" : "text-[15px]",
        )}
      >
        We-OS
      </span>
    </span>
  );
}
