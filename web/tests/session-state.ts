import { writeFile } from "node:fs/promises";

import type { BrowserContext } from "@playwright/test";

/**
 * Saves a signed-in browser context for the specs to start from, minus its
 * session token.
 *
 * A Clerk session token lives 60 s. The setup project signs in once at the
 * start of a run, so a spec that starts later than that would begin with a
 * token that has already expired — and how the middleware treats an expired
 * token depends on the request. A page navigation is renewed through a
 * handshake with Clerk. A server action or a client-side route change cannot
 * be: the middleware refuses any non-GET request whose token is more than 5 s
 * past expiry, and the page then reports a failed action, not a sign-in.
 *
 * A spec whose page loaded 4 s past expiry (inside the leeway, so no
 * handshake) and whose first action fired 5 s past it lost that action —
 * once in roughly 800 tests, and only in runs slow enough to push a spec
 * past the 60 s mark. That is the rotating failure the suite carried for a
 * week.
 *
 * With no token saved at all, the first navigation of every spec is renewed
 * through the handshake, and the spec runs on a token minted for it.
 * Everything else the sign-in produced — the client, the dev-browser
 * cookie, the active organization — is kept, since that is what the
 * handshake renews from.
 *
 * Args:
 *   context: The signed-in browser context.
 *   file: Where to write the storage state the specs will load.
 */
export async function saveRenewableSession(
  context: BrowserContext,
  file: string,
): Promise<void> {
  const state = await context.storageState();
  const cookies = state.cookies.filter(
    (cookie) => !cookie.name.startsWith("__session"),
  );
  await writeFile(file, JSON.stringify({ ...state, cookies }, null, 2));
}
