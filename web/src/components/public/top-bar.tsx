import Link from "next/link";

import { Container } from "@/components/public/section";
import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";

/**
 * Renders the public top bar: the brand mark, the section links, and the one
 * way in. "Get started" leads to Get Started, where a tier is chosen before an
 * account exists; the sign-up form is reached from there.
 *
 * Sticky and translucent so it stays in reach as the Landing scrolls; its
 * height is the `--top-bar-height` token, which the page's scroll padding
 * also reads, so an anchor never lands under it. Every link is absolute, so
 * the bar works from any public page, not only the Landing.
 */
export function PublicTopBar() {
  return (
    <header className="sticky top-0 z-20 border-b bg-white/80 backdrop-blur-md">
      <nav aria-label="Primary">
        <Container className="flex h-(--top-bar-height) items-center gap-8">
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
              <Link href="/get-started">Get started</Link>
            </Button>
          </div>
        </Container>
      </nav>
    </header>
  );
}
