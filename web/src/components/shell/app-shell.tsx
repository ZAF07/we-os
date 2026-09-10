"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Calendar,
  Home,
  Megaphone,
  Menu,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { UserButton, useOrganization, useUser } from "@clerk/nextjs";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { BrandMark } from "@/components/ui/brand-mark";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

/** The route the Brand DNA badge counts against. */
const BRAND_HREF = "/brand";

const NAV_ITEMS: NavItem[] = [
  { href: "/home", label: "Home", icon: Home },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/brand", label: "Brand", icon: BookOpen },
  { href: "/performance", label: "Performance", icon: TrendingUp },
];

/**
 * Decides whether a nav item is active for the current path.
 *
 * Args:
 *   href: The nav item's route.
 *   pathname: The current pathname.
 *
 * Returns:
 *   True when the item (or a route it owns, e.g. Workspace under
 *   Campaigns) is active.
 */
function isActive(href: string, pathname: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Renders the primary nav links with active state and the Brand DNA badge.
 *
 * Args:
 *   brandFieldsOwed: How many Required Brand DNA fields the business still
 *     owes. The badge is the gate made visible from anywhere in the app, so it
 *     rides the nav rather than one screen; zero hides it.
 *   onNavigate: Optional callback fired on link click (closes the
 *     mobile drawer).
 */
function NavLinks({
  brandFieldsOwed,
  onNavigate,
}: {
  brandFieldsOwed: number;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-0.5 px-2.5 py-1.5">
      {NAV_ITEMS.map((item) => {
        const active = isActive(item.href, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-[13.5px]",
              active
                ? "bg-indigo-50 font-semibold text-indigo-600"
                : "font-medium text-slate-700 hover:bg-slate-100",
            )}
          >
            <item.icon className="size-4 shrink-0" strokeWidth={2} />
            <span className="flex-1">{item.label}</span>
            {item.href === BRAND_HREF && brandFieldsOwed > 0 && (
              <span
                aria-label={`${brandFieldsOwed} Brand DNA answers still needed`}
                className="rounded-full bg-amber-100 px-1.5 text-[10.5px] font-bold text-amber-800"
              >
                {brandFieldsOwed}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

/**
 * Renders the operator card: the signed-in user, their business, and sign-out.
 *
 * The name and business come from Clerk's session, so the shell reflects who is
 * actually signed in.
 */
/**
 * Reports whether the component has mounted in the browser.
 *
 * `false` on the server and during hydration, `true` from the first render
 * after it — the one moment the server and the client are guaranteed to
 * agree on, whatever else has happened in the browser by then.
 */
function useMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

/**
 * Renders the signed-in person and their business at the foot of the rail.
 *
 * Clerk's `UserButton` renders its fallback until the Clerk script has
 * loaded, and its real host once it has. On the server the script has never
 * loaded, so the fallback is what gets serialised — but in the browser the
 * script can finish before React hydrates, and then the button hydrates as
 * its host against markup that holds the fallback. React answers a mismatch
 * by throwing the server tree away and re-rendering the whole page on the
 * client, which resets every component's state — a wizard mid-way through
 * its steps goes back to the first one. So the button is only rendered once
 * mounted: until then this shows the same fallback the server did.
 */
export function UserCard() {
  const { user } = useUser();
  const { organization } = useOrganization();
  const mounted = useMounted();
  const businessName = organization?.name ?? "Your business";

  const avatarFallback = (
    <div className="flex size-7 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
      M
    </div>
  );

  return (
    <div className="mt-auto flex items-center gap-2.5 border-t px-3.5 py-3">
      {mounted ? (
        <UserButton
          appearance={{ elements: { userButtonAvatarBox: "size-7" } }}
          fallback={avatarFallback}
        />
      ) : (
        avatarFallback
      )}
      <div className="min-w-0 leading-tight">
        <div className="truncate text-[13px] font-semibold">
          {user?.fullName ??
            user?.primaryEmailAddress?.emailAddress ??
            "Signed in"}
        </div>
        <div className="truncate text-[11.5px] text-muted-foreground">
          {businessName} workspace
        </div>
      </div>
    </div>
  );
}

/**
 * Renders the persistent application shell: desktop nav rail, mobile
 * drawer, and the content area.
 *
 * Only the signed-in half gets it: the `(app)` route group's layout renders
 * the shell and the public half never does, so where a page lives decides
 * whether it has one. There is no list of paths to keep in step.
 *
 * Args:
 *   brandFieldsOwed: How many Required Brand DNA fields the business still
 *     owes, read by the layout because a client component cannot fetch.
 *   children: The active route's content.
 */
export function AppShell({
  brandFieldsOwed,
  children,
}: {
  brandFieldsOwed: number;
  children: React.ReactNode;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex h-dvh flex-col overflow-hidden md:flex-row">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-card px-4 md:hidden">
        <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
          <SheetTrigger
            aria-label="Open navigation"
            className="rounded-lg p-1.5 hover:bg-slate-100"
          >
            <Menu className="size-5" />
          </SheetTrigger>
          <SheetContent side="left" className="w-64 gap-0 bg-card p-0">
            <SheetHeader className="px-[18px] pt-4 pb-3">
              <SheetTitle asChild>
                <BrandMark />
              </SheetTitle>
            </SheetHeader>
            <div className="flex flex-1 flex-col">
              <NavLinks
                brandFieldsOwed={brandFieldsOwed}
                onNavigate={() => setDrawerOpen(false)}
              />
              <UserCard />
            </div>
          </SheetContent>
        </Sheet>
        <BrandMark />
      </header>
      <aside className="hidden w-[216px] shrink-0 flex-col border-r bg-card md:flex">
        <div className="px-[18px] pt-4 pb-3">
          <BrandMark />
        </div>
        <NavLinks brandFieldsOwed={brandFieldsOwed} />
        <UserCard />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {children}
      </div>
    </div>
  );
}
