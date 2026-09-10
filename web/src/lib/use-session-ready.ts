"use client";

import { useClerk } from "@clerk/nextjs";

/**
 * Reports whether the session is ready to be used from the browser.
 *
 * A session token lives a minute, and Clerk's browser script keeps it fresh
 * while a page is open. A page opened cold — a restored tab, a bookmark, the
 * browser reopened — arrives with whatever token the cookie last held. The
 * page load itself is fine either way, because the middleware renews a stale
 * token through a handshake. What the page does next is not: a server action
 * cannot be renewed, so one fired before the script has refreshed the cookie
 * is refused as expired, and the person reads an error on a page they did
 * nothing wrong on. Clerk's loaded state is the moment the script has fetched
 * the client and written a fresh token, so a load that waits on it runs on a
 * token minted for it.
 *
 * Returns:
 *   True once Clerk's browser script has loaded — immediately on a page whose
 *   script already has, so a client-side navigation waits for nothing.
 */
export function useSessionReady(): boolean {
  return useClerk().loaded;
}
