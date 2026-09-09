import { BrandMark } from "@/components/ui/brand-mark";

/**
 * Wraps Welcome — the signed-in half's antechamber — in a layout of its own.
 *
 * A Tenantless Session is a third state. The app shell reads the organization
 * and the credits and would break for a session with no business, and the
 * public layout would offer a signed-in person a "Sign in" button. So this
 * group has a brand mark, a centred card, no navigation rail — there is no
 * product to navigate yet — and no engine call.
 *
 * Args:
 *   children: The active route's content.
 */
export default function WelcomeLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="flex h-(--top-bar-height) items-center px-5 md:px-10">
        <BrandMark size="large" />
      </header>
      <main className="flex flex-1 items-start justify-center px-5 py-10 md:items-center md:py-16">
        {children}
      </main>
    </div>
  );
}
