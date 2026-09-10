import { act } from "react";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * Whether Clerk's browser script has finished loading, as the mocked Clerk
 * components see it. Flipped between the server render and the client render
 * to reproduce the state a page is in when the script loads before React
 * hydrates — which is what happens on a slow dev server.
 */
let clerkLoaded = false;

vi.mock("@clerk/nextjs", () => ({
  useUser: () => ({ user: { fullName: "Zaf" } }),
  useOrganization: () => ({ organization: { name: "Summit" } }),
  UserButton: ({ fallback }: { fallback: React.ReactNode }) =>
    clerkLoaded ? (
      <div data-clerk-component="UserButton" style={{ display: "none" }} />
    ) : (
      fallback
    ),
}));

vi.mock("next/navigation", () => ({ usePathname: () => "/home" }));

const { UserCard } = await import("@/components/shell/app-shell");

let root: Root | null = null;
afterEach(() => {
  root?.unmount();
  root = null;
  clerkLoaded = false;
});

describe("UserCard", () => {
  it("hydrates cleanly when Clerk has already loaded on the client", async () => {
    clerkLoaded = false;
    const html = renderToString(<UserCard />);
    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.appendChild(container);

    // The script beat React to it: by the time the tree hydrates, Clerk's
    // components would render their real host instead of the fallback.
    clerkLoaded = true;
    const recoverable = vi.fn();
    await act(async () => {
      root = hydrateRoot(container, <UserCard />, {
        onRecoverableError: recoverable,
      });
    });

    expect(recoverable).not.toHaveBeenCalled();
    expect(
      container.querySelector('[data-clerk-component="UserButton"]'),
    ).not.toBeNull();
    expect(container.textContent).toContain("Zaf");
    expect(container.textContent).toContain("Summit workspace");
  });
});
