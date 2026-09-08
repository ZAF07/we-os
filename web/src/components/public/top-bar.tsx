import Link from "next/link";

import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";

/**
 * Renders the public top bar: the brand mark, the section links, and the one
 * way in.
 *
 * Sticky and translucent so it stays in reach as the Landing scrolls. Every
 * link is absolute, so the bar works from any public page, not only the
 * Landing.
 */
export function PublicTopBar() {
  return (
    <header className="sticky top-0 z-20 border-b bg-white/80 backdrop-blur-md">
      <nav
        aria-label="Primary"
        className="mx-auto flex h-[68px] max-w-[1180px] items-center gap-8 px-5 md:px-10"
      >
        <Link href="/" className="text-foreground">
          <BrandMark size="large" />
        </Link>
        <div className="hidden gap-7 text-[14.5px] font-medium text-slate-600 md:flex">
          <Link href="/#how" className="hover:text-foreground">
            How it works
          </Link>
          <Link href="/pricing" className="hover:text-foreground">
            Pricing
          </Link>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button asChild variant="outline">
            <Link href="/sign-in">Sign in</Link>
          </Button>
          <Button asChild>
            <Link href="/sign-up">Get started</Link>
          </Button>
        </div>
      </nav>
    </header>
  );
}
