# 06 — A page that fetches on mount waits for the session to be ready

Status: ready-for-agent
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

- [ ] With Clerk mocked as not yet loaded, neither the wizard's segment load
      nor the Workspace's stage load fires; once loaded, each fires exactly
      once. Asserted at the page seam by unit tests in the style of the
      wizard's existing ones.
- [ ] The wizard's retry-once and "Try again" behaviour and the Workspace's
      "Could not load this stage" path still pass their existing tests.
- [ ] When the session is already fresh, the mount-time load starts in the
      same render cycle it does today — no extra round trip and no visible
      loading state that was not there before, checked by a unit test that
      counts renders before the first call.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit`
      pass, and `make test-e2e` stays green.

## Blocked by

None — can start immediately.
