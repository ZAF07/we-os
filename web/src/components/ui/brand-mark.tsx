import Image from "next/image";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Renders the We-OS logo mark and wordmark.
 *
 * One component for every place the name appears — the app shell, the public
 * top bar and the footer — so the product has one name and one mark wherever
 * a person sees it. The mark is the logo artwork, which carries its own dark
 * rounded-square ground, so the tile needs no background of its own.
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
      <Image
        src="/we-os-mark.png"
        alt=""
        aria-hidden="true"
        width={120}
        height={120}
        priority={large}
        className={cn(
          large ? "size-[30px] rounded-[9px]" : "size-6 rounded-[7px]",
        )}
      />
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
