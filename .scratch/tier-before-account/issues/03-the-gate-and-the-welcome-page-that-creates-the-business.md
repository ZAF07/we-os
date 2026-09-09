# 03 — The gate, and the Welcome page that creates the business

Status: ready-for-human
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

- [ ] Signing up creates a login and no Organization; the new person is asked for their business name before reaching any part of the product.
- [ ] Naming a business at Welcome with a tier creates the Organization, records that tier against the tenant, and lands on Home.
- [ ] A failure recording the tier keeps the person on Welcome with a plain message and a retry that does not create a second Organization.
- [ ] Welcome with no tier goes to Get Started; Welcome with a business already active goes to Home; Welcome with no session goes to sign-in.
- [ ] A signed-in session with no business cannot reach Home, Campaigns, Calendar, Brand, Performance or Onboarding — each goes to Welcome.
- [x] A tenant with no tier that reaches Home is sent back to Welcome.
- [x] A person who is already signed in and picks a tier on Get Started is taken to Welcome, not to sign-up.
- [x] The Launch destination resolver is a pure function with unit tests covering signed-out and tenantless, with and without a tier.
- [x] An existing business owner signs in and reaches Home exactly as before, with campaigns, credits and Brand DNA untouched — the existing signed-in Playwright projects pass unchanged.
- [ ] A Playwright project runs as a tenantless session with its own Clerk user, asserting the redirects above, and deletes the Organization it creates so the fixture is tenantless for the next run. It runs single-worker, as the onboarding project does.
- [x] Turning off Clerk's create-organization-on-sign-up is documented in the web setup steps.
- [ ] `make check`, `make test-postgres`, the web gates and the Playwright suite pass, and the whole new-user flow is confirmed end to end in the running app.

## Blocked by

- [01 — Get Started, the page where a tier is chosen](01-get-started-the-page-where-a-tier-is-chosen.md)
- [02 — The engine owns the tier](02-the-engine-owns-the-tier.md)

## Comments

- 2026-09-09 — One redirect differs from the text above. "Welcome with a business already active goes to Home" and "a tenant with no tier that reaches Home is sent back to Welcome" loop for a business whose tier was never recorded: Welcome cannot see the recorded tier without an engine call it is designed not to make. So Home sends a tierless business to **Get Started** to choose, and Welcome, when it arrives with a tier *and* an active business, records the tier and continues to Home instead of bouncing. Every other redirect is as written. The Launch resolver therefore sends any signed-in session to Welcome with the tier — a business owner who arrives with a different tier than the one recorded sees the engine's 409 message and a link to Home. Recorded in CONTEXT.md (Welcome, Home) and ADR-0027's consequences.
- 2026-09-09 — The tenantless Playwright project needs a third Clerk test user (`E2E_CLERK_TENANTLESS_USER_EMAIL`) that belongs to no organization, and Clerk's organization-on-sign-up setting turned off. Both are dashboard steps documented in `web/README.md` and `web/.env.local.example`; neither can be made from the repository.
- 2026-09-09 — Implementation landed in `02892c1` (the gate, Welcome, Home's tier check, the sign-up destination, the session-aware Launch, the tenantless Playwright project), `8cc55e2` (code review: the Welcome form takes a `Tier`, a refused tier change is shown without a retry), `6b3d4ec` (the tenantless project skips, saying why, until its user exists) and `77880c1` (glossary and ADR-0027 amendments). Proven on the final code: the full suite passed 64 with the 6 tenantless tests skipped; `/welcome` sends a business owner to Home and a different tier is refused (`smoke.spec.ts`); with the blank tenant's tier cleared in the e2e database, Home sent it to Get Started, Launch led to `/welcome?tier=command`, the tier was recorded and Home followed (a throwaway spec, not kept); Welcome with no session goes to sign-in (`public.spec.ts`); the resolver's unit tests pass. **Not proven, and why:** deactivating the blank user's organization in the browser was a no-op, which is what Clerk does while its organization requirement on sign-up is on — so no existing user can be made tenantless, a new sign-up would be held in a pending session, and criteria 1, 2 (the Organization created from the form), 3, 4 (the tenantless clause), 5 and 10 could not be exercised. **What a person must do:** in the Clerk dashboard, turn off the organization requirement on sign-up and create a third test user (`E2E_CLERK_TENANTLESS_USER_EMAIL`) in no organization; set the variable in `web/.env.local`; run `make test-e2e` — the tenantless project then runs instead of skipping and covers the remaining criteria. Hence `ready-for-human`.
- 2026-09-09 — Merged to main as `b6c878f` (Merge: a tier is chosen before an account exists, and the platform creates the tenant); the code is live, the issue stays open for the human steps above.
