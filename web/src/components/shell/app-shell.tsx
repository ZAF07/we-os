"use client";

import { useEffect, useState } from "react";
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

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useDemoStore } from "@/lib/store";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: Home },
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
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Renders the Marketing OS logo mark and wordmark. */
function BrandMark() {
  return (
    <div className="flex items-center gap-[9px]">
      <div className="flex size-6 items-center justify-center rounded-[7px] bg-gradient-to-br from-indigo-600 to-indigo-500 text-[13px] font-bold text-white">
        M
      </div>
      <div className="text-[15px] font-bold tracking-tight">Marketing OS</div>
    </div>
  );
}

/**
 * Renders the primary nav links with active state and the Home badge.
 *
 * Args:
 *   onNavigate: Optional callback fired on link click (closes the
 *     mobile drawer).
 */
function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const approved = useDemoStore((state) => state.approved);

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
            {item.href === "/" && !approved && (
              <span className="rounded-full bg-indigo-50 px-[7px] py-px text-[11px] font-bold text-indigo-600">
                4
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

/** Renders the operator card with the active company workspace name. */
function UserCard() {
  const companyName = useDemoStore(
    (state) => state.onboarding?.companyName ?? "Fernway",
  );

  return (
    <div className="mt-auto flex items-center gap-2.5 border-t px-3.5 py-3">
      <div className="flex size-7 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
        M
      </div>
      <div className="leading-tight">
        <div className="text-[13px] font-semibold">Maya Chen</div>
        <div className="text-[11.5px] text-muted-foreground">
          {companyName} workspace
        </div>
      </div>
    </div>
  );
}

/**
 * Renders the persistent application shell: desktop nav rail, mobile
 * drawer, and the content area. Also rehydrates the demo store from
 * sessionStorage on mount.
 *
 * Args:
 *   children: The active route's content.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    void useDemoStore.persist.rehydrate();
  }, []);

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
              <NavLinks onNavigate={() => setDrawerOpen(false)} />
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
        <NavLinks />
        <UserCard />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {children}
      </div>
    </div>
  );
}
