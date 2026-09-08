import { AppShell } from "@/components/shell/app-shell";

/**
 * Wraps the signed-in half in the app shell.
 *
 * Every route under this group needs a session; the proxy sends a signed-out
 * request to sign-in before it gets here. A page gets the shell by living in
 * this folder, so there is no list of paths deciding when to show it.
 *
 * Args:
 *   children: The active route's content.
 */
export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <AppShell>{children}</AppShell>;
}
