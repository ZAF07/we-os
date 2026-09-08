# 01 — Split the app into public and signed-in halves, with a bare Landing

Status: completed
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../../archive/PRD.md) · [ADR-0012](../../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md) (2026-09-08 amendment) · [ADR-0013](../../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)

## What to build

The web app gets its two natural halves. A public half (Landing, Pricing later, sign-in, sign-up) renders without the app shell and without a session. A signed-in half (Home, Campaigns, Calendar, Brand, Performance, Onboarding) keeps the shell and keeps requiring a session. Use Next.js route groups with one layout each, the standard convention; delete the shell's hardcoded list of "bare" paths, since the folder structure now decides.

Home moves from the root to `/home`. The nav rail's Home link follows it. The middleware opens the root, sign-in, and sign-up to visitors; a signed-in session that opens the root is redirected to Home. Sign-in and sign-up fall back to Home after completion (Clerk fallback-redirect settings), so a new business owner sees Home and, from there, onboarding.

The root becomes the **Landing**, in this slice reduced to its skeleton: a top bar (We-OS brand mark, "Sign in" outline button, "Get started" primary button), the locked hero, and a plain footer. Hero headline: "Strategy before content. Always." Subline: "Augmented workflow for digital marketing. Expert practice built in, your judgement kept in. Answer the questions only you can answer, review each decision as it lands, and approve what runs." Buttons: "Get started" (to sign-up) and "See how it works" (outline; scrolls to the steps section, which arrives in issue 03, so for now it points at an anchor that later issues fill). Built from the existing theme tokens and primitives; light theme; stacks on mobile; no images; no engine calls.

The product name becomes **We-OS** everywhere the public sees it: the shell brand mark, the browser title and description, and the sign-in and sign-up headings. Home's user-facing "Allowance" strings become "Credits" (the `allowance` identifier in code is not renamed).

Testing: add one Playwright project that runs the public specs with no saved session. Update the smoke and home specs to Home's new address, the We-OS brand mark, and the "Credits" label.

## Acceptance criteria

- [x] With no session, the root returns 200 and shows the hero headline, "Sign in", and "Get started"; no app shell, no engine error.
- [x] With no session, `/home` redirects to sign-in and returns to `/home` after signing in.
- [x] Signed in, opening the root lands on `/home`, and Home shows its four sections with a "Credits" card.
- [x] Signed in, the nav rail's Home link goes to `/home` and marks itself active; every other primary route still resolves with the shell.
- [x] "Sign in" and "Get started" open the existing Clerk sign-in and sign-up pages; completing either lands on Home.
- [x] The shell brand mark, browser title, and auth page headings read "We-OS"; "Marketing OS" appears nowhere as the product name.
- [x] The shell contains no path list deciding when to hide itself; route groups do that.
- [x] A Playwright project with no storage state exists and runs the public spec; smoke and home specs pass against `/home`.
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

None - can start immediately

## Completion

- Completed: 2026-09-08
- Commits:
  - `ac6557e` Split the app into public and signed-in halves, with a bare Landing
  - `fc5d251` Address code review: vocabulary, one pricing intro, one height token, no animation
  - `b78329f` Document the public half in the web README and env example
  - merged to main as `00c13af` Merge: We-OS Landing and Pricing, the public half of the app

### Evidence

- **Criterion 1** — `web/tests/public.spec.ts` "the root is the Landing, open to a visitor" runs in the `chromium-public` project with no session: asserts status 200 at `/`, the hero headline, "Sign in" and "Get started" in the banner, and that no `aside` (the nav rail) exists. The Landing is a static server component with no engine call (`web/src/app/(public)/page.tsx`).
- **Criterion 2** — "Home without a session is sent to sign-in, and remembers where to return": `/home` lands on `/sign-in` with the decoded URL carrying `/home` (`web/src/proxy.ts`, `redirectToSignIn` with the request URL as the return address). The return after sign-in is Clerk's `redirect_url` handling, and the fallback for a sign-in with no return address is pinned by `web/tests/smoke.spec.ts` "signed in, the sign-in page hands straight over to Home".
- **Criterion 3** — `web/tests/smoke.spec.ts` "opening the root signed in lands on Home, never the Landing" (the proxy redirects a signed-in `/` to `/home`, `web/src/proxy.ts:37-39`); `web/tests/home.spec.ts` "home renders its sections" asserts Action queue, In progress now, Credits and Portfolio at `/home`. Home's "Allowance" strings had already become "Credits" in `1ebf441`, so nothing was left to rename.
- **Criterion 4** — `web/src/components/shell/app-shell.tsx:34` points Home at `/home`; "nav rail reaches every primary route and marks it active", "all routes resolve without a 404" and "workspace route highlights the Campaigns nav item" pass against the new address.
- **Criterion 5** — "Get started and Sign in open the sign-up and sign-in flows" reaches both Clerk pages and their "We-OS" heading. Both components fall back to Home (`fallbackRedirectUrl="/home"` in `web/src/app/(public)/sign-in/[[...sign-in]]/page.tsx:21` and `sign-up/[[...sign-up]]/page.tsx:24`); the smoke test above exercises that fallback in a real browser. A full email-code sign-in cannot be driven by the suite, which signs in through Clerk's testing helper instead.
- **Criterion 6** — `grep -rn "Marketing OS" web/src web/tests` is empty. The shared `web/src/components/ui/brand-mark.tsx` renders the "W" mark and "We-OS" for the shell, the top bar and the footer; `web/src/app/layout.tsx:12` sets the title `We-OS` with a `%s · We-OS` template; both auth pages head with "We-OS"; `auth.setup.ts` and `smoke.spec.ts` assert the rail reads "We-OS".
- **Criterion 7** — `BARE_ROUTES` and the `pathname.startsWith` check are gone from `app-shell.tsx`; `web/src/app/(app)/layout.tsx` renders the shell and `web/src/app/(public)/layout.tsx` renders the top bar and footer, so the folder decides.
- **Criterion 8** — `web/playwright.config.ts:80` adds `chromium-public` with no `storageState` and no `dependencies`; `chromium` ignores the public spec. Smoke and home specs pass against `/home` in the 60/60 run.
- **Criterion 9** — `pnpm typecheck`, `pnpm lint`, `pnpm format:check` and `pnpm test:unit` (8 files, 72 tests) pass. `pnpm test` was run against a freshly started e2e stack (`make e2e-up`, then `E2E_STACK=compose pnpm test`): **60 passed, 0 failed** across the `setup`, `chromium`, `chromium-onboarding` and `chromium-public` projects, on the final code (`b78329f`). On a stack that had already absorbed five suite runs, the campaign-creating specs failed in the way [e2e-suite-flake 01](../../../e2e-suite-flake/issues/01-campaign-creating-specs-fail-under-parallel-workers.md) documents; a note with today's numbers was added there. Checked in the running app: full-page screenshots of `/`, `/pricing` and `/sign-in` at 1280px and 375px.
