# 01 — Split the app into public and signed-in halves, with a bare Landing

Status: ready-for-agent
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../PRD.md) · [ADR-0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md) (2026-09-08 amendment) · [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)

## What to build

The web app gets its two natural halves. A public half (Landing, Pricing later, sign-in, sign-up) renders without the app shell and without a session. A signed-in half (Home, Campaigns, Calendar, Brand, Performance, Onboarding) keeps the shell and keeps requiring a session. Use Next.js route groups with one layout each, the standard convention; delete the shell's hardcoded list of "bare" paths, since the folder structure now decides.

Home moves from the root to `/home`. The nav rail's Home link follows it. The middleware opens the root, sign-in, and sign-up to visitors; a signed-in session that opens the root is redirected to Home. Sign-in and sign-up fall back to Home after completion (Clerk fallback-redirect settings), so a new business owner sees Home and, from there, onboarding.

The root becomes the **Landing**, in this slice reduced to its skeleton: a top bar (We-OS brand mark, "Sign in" outline button, "Get started" primary button), the locked hero, and a plain footer. Hero headline: "Strategy before content. Always." Subline: "Augmented workflow for digital marketing. Expert practice built in, your judgement kept in. Answer the questions only you can answer, review each decision as it lands, and approve what runs." Buttons: "Get started" (to sign-up) and "See how it works" (outline; scrolls to the steps section, which arrives in issue 03, so for now it points at an anchor that later issues fill). Built from the existing theme tokens and primitives; light theme; stacks on mobile; no images; no engine calls.

The product name becomes **We-OS** everywhere the public sees it: the shell brand mark, the browser title and description, and the sign-in and sign-up headings. Home's user-facing "Allowance" strings become "Credits" (the `allowance` identifier in code is not renamed).

Testing: add one Playwright project that runs the public specs with no saved session. Update the smoke and home specs to Home's new address, the We-OS brand mark, and the "Credits" label.

## Acceptance criteria

- [ ] With no session, the root returns 200 and shows the hero headline, "Sign in", and "Get started"; no app shell, no engine error.
- [ ] With no session, `/home` redirects to sign-in and returns to `/home` after signing in.
- [ ] Signed in, opening the root lands on `/home`, and Home shows its four sections with a "Credits" card.
- [ ] Signed in, the nav rail's Home link goes to `/home` and marks itself active; every other primary route still resolves with the shell.
- [ ] "Sign in" and "Get started" open the existing Clerk sign-in and sign-up pages; completing either lands on Home.
- [ ] The shell brand mark, browser title, and auth page headings read "We-OS"; "Marketing OS" appears nowhere as the product name.
- [ ] The shell contains no path list deciding when to hide itself; route groups do that.
- [ ] A Playwright project with no storage state exists and runs the public spec; smoke and home specs pass against `/home`.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

None - can start immediately
