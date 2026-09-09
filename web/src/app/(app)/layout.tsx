import { AppShell } from "@/components/shell/app-shell";
import { getBrandDnaCompleteness } from "@/lib/engine";

export const dynamic = "force-dynamic";

/**
 * Wraps the signed-in half in the app shell.
 *
 * Every route under this group needs a session; the proxy sends a signed-out
 * request to sign-in before it gets here. A page gets the shell by living in
 * this folder, so there is no list of paths deciding when to show it.
 *
 * The Brand DNA gate is read here rather than on Home because it blocks every
 * campaign stage there is, so the count belongs on every signed-in route — and
 * the shell is a client component, which cannot fetch. Reading it here costs a
 * second read on Home, which also needs it for the queue; that is cheaper than
 * threading one read up from a page to the layout that renders around it.
 *
 * Args:
 *   children: The active route's content.
 */
export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const brandFieldsOwed = await countBrandFieldsOwed();
  return <AppShell brandFieldsOwed={brandFieldsOwed}>{children}</AppShell>;
}

/**
 * Counts the Required Brand DNA fields the business still owes.
 *
 * Returns:
 *   How many fields are missing, and zero when the Brand DNA is complete or
 *   the read failed — a badge is worth less than the shell it sits in, so a
 *   failure here costs the badge alone.
 */
async function countBrandFieldsOwed(): Promise<number> {
  try {
    const completeness = await getBrandDnaCompleteness();
    return completeness.complete ? 0 : completeness.missing.length;
  } catch {
    return 0;
  }
}
