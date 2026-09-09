# 03 — The gate, and the Welcome page that creates the business

Status: completed
Type: task

## Parent

[PRD: A tier before an account](../PRD.md) · [ADR-0027](../../../docs/adr/0027-the-platform-creates-the-tenant-and-owns-the-tier.md) · [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md) · [ADR-0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md)

## What to build

We-OS stops letting the identity provider decide when one of its businesses comes into being.

**Clerk stops creating Organizations on sign-up.** This is a dashboard setting, not a code change, and it is the one thing here that cannot be made in the repository. Missed on a fresh Clerk instance, sign-up creates an Organization behind the app's back and the gate silently never fires, with no error anywhere — so it is written into the web setup steps as part of this work.

A new sign-up therefore lands authenticated with no organization claim — a **Tenantless Session**. The app half is closed to them.

**A third route group for Welcome**, with its own minimal layout: brand mark, a centred card, no navigation rail, no engine call. A tenantless session is genuinely a third state — the app shell reads the organization and the credits and would break for it, and the public layout would show a signed-in person a "Sign in" button.

**The Welcome page** asks for the business name. On submit it creates the Organization, activates it on the session, then records the chosen **Tier** through the endpoint from issue 02, then goes to **Home**. The ordering is forced and must be kept: the Organization must exist before the session can carry an organization claim, and the session must carry that claim before the engine can mint the tenant the tier attaches to. Activation mutates the browser's session, which is why the sequence runs on the client rather than being split across a server action.

A failure at the tier call leaves the person on the page with a plain message and a retry. The Organization already exists by then, so the retry is the tier call alone — which is why that call is safe to repeat.

Welcome with no tier goes to **Get Started** to choose one. Welcome with a business already active goes to Home.

**The gate** lives in the proxy: a signed-in session whose token carries no organization claim may reach only Welcome, Get Started and the public routes; anything else in the app half goes to Welcome. It is cheap — the claim is already in the token, so no engine call is needed on any request. This is a convenience, not the security boundary: the engine independently refuses a token with no organization claim, and that is what actually protects tenant data (ADR-0013). The gate exists so a person gets a way forward instead of a 401.

**A tier check on Home's server load** sends a tenant with no tier back to Welcome. One route, not every request. It closes the only state in the flow where a business exists without a tier — between activating the Organization and recording the tier.

**The sign-up page** reads its own tier parameter and sets its post-authentication destination to Welcome carrying that tier, falling back to bare Welcome when absent, which then bounces to Get Started. Its sign-in fallback stays Home: an existing person signing in from the sign-up form has a business and needs no welcome.

**Get Started's Launch buttons resolve their destination from the session** — signed out to sign-up with the tier, signed in without a business to Welcome with the tier — so a person who signed in before choosing is not sent to create an account they already have. That resolution is a pure function, tested as one. Get Started now reads the Clerk session but still makes no engine call, so the public half's no-engine property holds.

Route addresses and tier names are not restated here: the tier comes from the tier module, and the destinations are the addresses the app already uses.

## Acceptance criteria

- [x] Signing up creates a login and no Organization; the new person is asked for their business name before reaching any part of the product.
- [x] Naming a business at Welcome with a tier creates the Organization, records that tier against the tenant, and lands on Home.
- [x] A failure recording the tier keeps the person on Welcome with a plain message and a retry that does not create a second Organization.
- [x] Welcome with no tier goes to Get Started; Welcome with a business already active goes to Home; Welcome with no session goes to sign-in.
- [x] A signed-in session with no business cannot reach Home, Campaigns, Calendar, Brand, Performance or Onboarding — each goes to Welcome.
- [x] A tenant with no tier that reaches Home is sent back to Welcome.
- [x] A person who is already signed in and picks a tier on Get Started is taken to Welcome, not to sign-up.
- [x] The Launch destination resolver is a pure function with unit tests covering signed-out and tenantless, with and without a tier.
- [x] An existing business owner signs in and reaches Home exactly as before, with campaigns, credits and Brand DNA untouched — the existing signed-in Playwright projects pass unchanged.
- [x] A Playwright project runs as a tenantless session with its own Clerk user, asserting the redirects above, and deletes the Organization it creates so the fixture is tenantless for the next run. It runs single-worker, as the onboarding project does.
- [x] Turning off Clerk's create-organization-on-sign-up is documented in the web setup steps.
- [x] `make check`, `make test-postgres`, the web gates and the Playwright suite pass, and the whole new-user flow is confirmed end to end in the running app.

## Blocked by

- [01 — Get Started, the page where a tier is chosen](01-get-started-the-page-where-a-tier-is-chosen.md)
- [02 — The engine owns the tier](02-the-engine-owns-the-tier.md)

## Comments

- 2026-09-09 — One redirect differs from the text above. "Welcome with a business already active goes to Home" and "a tenant with no tier that reaches Home is sent back to Welcome" loop for a business whose tier was never recorded: Welcome cannot see the recorded tier without an engine call it is designed not to make. So Home sends a tierless business to **Get Started** to choose, and Welcome, when it arrives with a tier *and* an active business, records the tier and continues to Home instead of bouncing. Every other redirect is as written. The Launch resolver therefore sends any signed-in session to Welcome with the tier — a business owner who arrives with a different tier than the one recorded sees the engine's 409 message and a link to Home. Recorded in CONTEXT.md (Welcome, Home) and ADR-0027's consequences.
- 2026-09-09 — The tenantless Playwright project needs a third Clerk test user (`E2E_CLERK_TENANTLESS_USER_EMAIL`) that belongs to no organization, and Clerk's organization-on-sign-up setting turned off. Both are dashboard steps documented in `web/README.md` and `web/.env.local.example`; neither can be made from the repository.
- 2026-09-09 — Implementation landed in `02892c1` (the gate, Welcome, Home's tier check, the sign-up destination, the session-aware Launch, the tenantless Playwright project), `8cc55e2` (code review: the Welcome form takes a `Tier`, a refused tier change is shown without a retry), `6b3d4ec` (the tenantless project skips, saying why, until its user exists) and `77880c1` (glossary and ADR-0027 amendments). Proven on the final code: the full suite passed 64 with the 6 tenantless tests skipped; `/welcome` sends a business owner to Home and a different tier is refused (`smoke.spec.ts`); with the blank tenant's tier cleared in the e2e database, Home sent it to Get Started, Launch led to `/welcome?tier=command`, the tier was recorded and Home followed (a throwaway spec, not kept); Welcome with no session goes to sign-in (`public.spec.ts`); the resolver's unit tests pass. **Not proven, and why:** deactivating the blank user's organization in the browser was a no-op, which is what Clerk does while its organization requirement on sign-up is on — so no existing user can be made tenantless, a new sign-up would be held in a pending session, and criteria 1, 2 (the Organization created from the form), 3, 4 (the tenantless clause), 5 and 10 could not be exercised. **What a person must do:** in the Clerk dashboard, turn off the organization requirement on sign-up and create a third test user (`E2E_CLERK_TENANTLESS_USER_EMAIL`) in no organization; set the variable in `web/.env.local`; run `make test-e2e` — the tenantless project then runs instead of skipping and covers the remaining criteria. Hence `ready-for-human`.
- 2026-09-09 — Merged to main as `b6c878f` (Merge: a tier is chosen before an account exists, and the platform creates the tenant); the code is live, the issue stays open for the human steps above.
- 2026-09-09 — With `E2E_CLERK_TENANTLESS_USER_EMAIL` set, the tenantless setup fails with the session `pending` on Clerk's `choose-organization` task. The setting that causes it is the instance's Organizations setting **Membership required** (the default for instances created after 22 August 2025); it must be **Membership optional** (Personal Accounts on). The setup now names the task and that setting; `web/README.md` and `web/.env.local.example` say the same. Once switched, `make test-e2e` runs the five remaining specs.
- 2026-09-09 — With "Membership optional" on and the test user provisioned, the tenantless setup still failed at the form: Clerk refused with "Organization creation is not enabled for this user", because Clerk stamps that permission onto each user from the instance default in force when the user was created. The setup now repairs the dedicated user's flag and says so (`d41b0cd`). `make test-e2e` then passed 70 of 70.

## Completion

- Completed: 2026-09-09
- Commits, on branch `tier-before-account` and the two follow-up branches:
  - `02892c1` The gate, and the Welcome page that creates the business
  - `8cc55e2` Address code review: one set-once judgement, honest docstrings, real assertions
  - `6b3d4ec` Skip the tenantless project, saying why, until its Clerk user is provisioned
  - `77880c1` Glossary and ADR-0027: where Launch leads when signed in, and what guards the backfill
  - merged to main as `b6c878f` Merge: a tier is chosen before an account exists, and the platform creates the tenant
  - `f1e281b` Tenantless setup names the Clerk task and the setting that holds the session, merged as `6c07839`
  - `d41b0cd` The tenantless setup lets its user create organizations, merged as `68019a5`

### Evidence

- **Criterion 1** — Clerk's Organizations setting is "Membership optional", so sign-up creates a login and no Organization: the dedicated tenantless user signs in to an active session with no organization (`tests/tenantless.setup.ts`, which refuses a pending session). "a session with no business is sent from every route in the app half to Welcome" (`tests/tenantless.spec.ts`) proves that person reaches nothing before naming the business. The sign-up page's post-authentication destination is Welcome (`forceRedirectUrl` in `web/src/app/(public)/sign-up/[[...sign-up]]/page.tsx`).
- **Criterion 2** — "naming the business at Welcome creates it, records the tier, and lands on Home": fills the name, creates the Organization from the browser, lands on Home with the business name in the rail. The tier is recorded through `recordTier` → `PUT /tenant/tier`.
- **Criterion 3** — By code, not by a runtime failure: `web/src/components/welcome/welcome-form.tsx` creates the Organization only while `created` is false, flips it before recording the tier, and its retry calls `finish()` alone — the tier call — so a second Organization cannot be created. The refused-tier branch (a change that no retry can fix) is exercised by `smoke.spec.ts` "Welcome sends a business owner to Home, and never changes their tier". No spec induces a transient engine failure.
- **Criterion 4** — "Welcome with no tier, or a tier that does not exist, sends the person to choose one" (tenantless); "Welcome sends a business owner to Home" (smoke); "Welcome without a session is sent to sign-in" (public).
- **Criterion 5** — "a session with no business is sent from every route in the app half to Welcome" walks Home, Campaigns, Calendar, Brand, Performance and Onboarding and finds `/welcome` in each redirect chain.
- **Criterion 6** — "a business whose tier was never recorded is sent from Home to choose, and Launch finishes it": an Organization built around the app, activated on the session; Home sends it to Get Started (not bare Welcome — see the first comment), Launch leads to Welcome with the tier, which records it and lands on Home.
- **Criterion 7** — "Launch on Get Started leads a signed-in person to Welcome, not to a sign-up form": all three Launch links carry `/welcome?tier=<name>`.
- **Criterion 8** — `web/src/lib/tiers.ts` `launchHref`, `welcomeHref`, `tierFromParam`; `web/src/lib/tiers.test.ts` covers signed-out and signed-in, and Welcome with and without a tier (80 unit tests pass).
- **Criterion 9** — The `setup`, `chromium`, `chromium-onboarding` and `chromium-public` projects pass unchanged apart from the two Welcome assertions added to `smoke.spec.ts` and `public.spec.ts`; the seed writes the recommended tier so neither existing business meets the gate.
- **Criterion 10** — `chromium-tenantless` in `web/playwright.config.ts`: its own `setup-tenantless` project, one worker, `fullyParallel: false`; `afterEach` deletes every Organization the user belongs to through Clerk's Backend API (`tests/clerk-backend.ts`), and the setup deletes leftovers and repairs the user's create-organization flag before signing in.
- **Criterion 11** — `web/README.md` ("The tenantless session") and `web/.env.local.example` (checklist item 1) name the two Clerk settings: "Membership optional" (Personal Accounts on) and "allow users to create organizations".
- **Criterion 12** — `make check` 644 passed / 110 skipped and `make test-postgres` 754 passed on the branch; web typecheck, lint, format and 80 unit tests pass; `make test-e2e` on the final code: **70 passed**, including the six tenantless tests, so the new-user flow is confirmed end to end in the running app.
