import { PublicFooter } from "@/components/public/footer";
import { PublicTopBar } from "@/components/public/top-bar";

/**
 * Wraps the public half — the Landing, Pricing, Get Started and the sign-in
 * and sign-up flows — in a top bar and footer of its own, with no app shell.
 *
 * Args:
 *   children: The active route's content.
 */
export default function PublicLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-dvh flex-col bg-card">
      <PublicTopBar />
      <div className="flex flex-1 flex-col">{children}</div>
      <PublicFooter />
    </div>
  );
}
