# 06 — A page that fetches on mount waits for the session to be ready

Status: completed
Type: task

## Parent

[04 — The e2e suite still drops a rotating spec or two under parallel load](archive/04-the-suite-still-drops-a-rotating-spec-under-parallel-load.md)

## What to build

A Clerk session token lives 60 s, and Clerk's browser script keeps it fresh
while a page is open. A page opened cold — a restored tab, a bookmark, the
browser reopened — arrives with whatever token the cookie last held. The
page load itself is fine either way: a token more than 5 s past expiry is
renewed through a handshake, and one inside that 5 s leeway is accepted as
is. The trouble is what the page does next. The new-campaign wizard loads
its Audience Segments the moment it mounts, and the Workspace loads the
selected stage the moment it mounts; both are server actions, and a server
action cannot be renewed. If the page loaded inside the leeway and the
action fires before the script has refreshed the cookie — about a second
after mount, before the script is done — the middleware refuses it as
expired, the built-in retry hits the same token 300 ms later, and the
business owner reads "We could not load your audience segments — Try again"
or "Could not load this stage. Try again." on a page they did nothing wrong
on. The retry works, because by then the script has refreshed. Issue 04
caught this once in ~1,100 suite runs' worth of tests; a person hits it in
the five-second band around expiry on a cold open.

Make a page that calls the engine on mount wait until the session is ready
to be used: one hook, answered from Clerk's loaded state, that the two
mount-time loads consult before firing. The action fires exactly once, after
readiness, and the existing retry and "Try again" paths are unchanged for
the failures they were written for (a transient engine blip, an empty Brand
DNA). Nothing changes for a page whose session is already fresh — readiness
is immediate there, and the load must not be delayed by a render.

## Acceptance criteria

- [x] With Clerk mocked as not yet loaded, neither the wizard's segment load
      (`page.test.tsx` "waits for the session to be ready, then asks for the
      segments once" and `workspace.test.tsx` "waits for the session to be
      ready, then loads the stage once": not called while `loaded` is false,
      called exactly once after it flips, still once after a further render.
      Both red without the hook wired in.)
      nor the Workspace's stage load fires; once loaded, each fires exactly
      once. Asserted at the page seam by unit tests in the style of the
      wizard's existing ones.
- [x] The wizard's retry-once and "Try again" behaviour and the Workspace's
      (The wizard's six existing tests pass unchanged; the Workspace had no
      unit tests, so `workspace.test.tsx` adds "says the stage could not be
      loaded when the load itself fails" for its "Could not load this stage"
      path.)
      "Could not load this stage" path still pass their existing tests.
- [x] When the session is already fresh, the mount-time load starts in the
      ("asks for the segments in its first render when the session is already
      ready" and "loads the stage in its first render when the session is
      already ready": renders are counted at the hook, and the first call
      lands after exactly one.)
      same render cycle it does today — no extra round trip and no visible
      loading state that was not there before, checked by a unit test that
      counts renders before the first call.
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit`
      (All clean; 120 unit tests in 13 files. `make test-e2e` 73 passed, and
      the fourteen gate runs in issue 05 all carried this change.)
      pass, and `make test-e2e` stays green.

## Blocked by

None — can start immediately.

## Comments

### Done (2026-09-10)

Landed as `bec7658`, with review fixes in `511877c`, on branch
`e2e-flake-followups`.

**The hook** is `useSessionReady` in `web/src/lib/use-session-ready.ts`, and it
answers `useClerk().loaded`. Not `useAuth().isLoaded`: in the Next.js
integration `ClerkProvider` hands the client the server's auth state, so
`isLoaded` is already `true` on the very first render, before the browser
script has run — it would never have waited. `loaded` is the IsomorphicClerk's
own flag, set once `clerk-js` has fetched the client and written the fresh
session token to the cookie, and the provider re-renders its consumers on that
status change (it is what `<ClerkLoaded>` reads).

**Where it is consulted.** The wizard's segment-load effect and the
Workspace's stage-load effect each return early until the hook answers `true`
and carry it in their dependencies, so the load fires exactly once on the
false→true edge and, on a page whose script has already loaded, in the first
render as before. Nothing else about either load changed: the wizard's
retry-once and abandon-on-retry, and the Workspace's re-read on a new version,
are as they were.

## Completion

- Completed: 2026-09-10
- Commit: bec7658, with review fixes in 511877c on branch `e2e-flake-followups` (merged to main in 9a4fc6f)
