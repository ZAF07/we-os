import Link from "next/link";

import { Container } from "@/components/public/section";
import { BrandMark } from "@/components/ui/brand-mark";

/**
 * Renders the public footer: the brand mark, the way in, and the copyright.
 *
 * It links only to pages that exist. There is no terms, privacy or contact
 * page yet, so none is promised here.
 */
export function PublicFooter() {
  return (
    <footer className="border-t">
      <Container className="flex flex-wrap items-center gap-6 py-8 text-sm text-slate-500">
        <Link href="/" className="text-foreground">
          <BrandMark />
        </Link>
        <Link href="/pricing" className="hover:text-foreground">
          Pricing
        </Link>
        <Link href="/sign-in" className="hover:text-foreground">
          Sign in
        </Link>
        <span className="ml-auto">© {new Date().getFullYear()} We-OS</span>
      </Container>
    </footer>
  );
}
