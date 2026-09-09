# PRD: A tier before an account — the platform creates the tenant

Status: completed
Category: feature
Date: 2026-09-09

Governed by [ADR-0027](../../docs/adr/0027-the-platform-creates-the-tenant-and-owns-the-tier.md) (written with this PRD), and by [0012](../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md), [0013](../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md), [0014](../../docs/adr/0014-postgres-system-of-record-and-split-governance.md), [0020](../../docs/adr/0020-usage-ledger-and-enforced-quota.md), [0025](../../docs/adr/0025-one-campaign-one-person-and-a-single-worker.md). Vocabulary per [CONTEXT.md](../../CONTEXT.md): **Tenant**, **Tier**, **Credits**, **Landing**, **Pricing**, **Get Started**, **Welcome**, **Tenantless Session**, **Home**, **Brand DNA**.

## Problem Statement

A person who opens We-OS, clicks "Get started", and signs up gets a working account without ever choosing a tier.

Clerk is configured to create an Organization during its own hosted sign-up, so the moment authentication completes the business exists: an Organization in the identity provider, a tenant row on the first engine call, and the whole product open to them. Nothing asked what they were signing up for. They go straight from an email address to naming their organization to a working account.

The tier is not merely unrecorded — there is nowhere to record it. The `tenants` table has no tier column, the engine has no notion that tiers exist, and the only trace of a visitor's choice is a `tier` query parameter that the sign-up page carries and nothing reads. The landing PRD said so plainly: *"Nothing reads it yet; it is carried until billing exists."*

Two things are wrong with that, and only one is about billing.

The first is the seam. When payment lands there is no step to put it in, because the flow has no moment between "I want this" and "I have an account". Retrofitting one means changing the shape of sign-up after people are using it.

The second is true today, with no payment involved: We-OS lets the identity provider decide when one of its businesses comes into being. A tenant is the isolation boundary for every document, run and checkpoint in the system, and it is currently created as a side effect of a vendor's sign-up form, on that vendor's schedule, in response to a form we do not own.

The generic "Get started" buttons compound it. The top bar, the hero and the final call all go straight to sign-up, so the most travelled path to an account is the one that skips the prices entirely. A visitor can reach a working account having never seen what We-OS costs.

## Solution

**A tier is chosen before an account exists, and We-OS creates the business.**

A new public page, **Get Started**, shows the same three tiers and the same questions as **Pricing**, under a heading that asks for the decision rather than explaining the prices. Every generic "Get started" button on the public half leads there, because a tier is chosen before an account exists. Its tier buttons say **Launch** — the action that will one day open checkout, and today opens sign-up carrying the chosen tier.

Clerk stops creating Organizations. It authenticates a person; it does not author a business. A new sign-up therefore lands authenticated with no organization claim — a **Tenantless Session** — and the app half is closed to them. They may reach only Get Started and **Welcome**, a new page in its own route group where they name their business. Welcome creates the Organization, activates it on the session, and records the chosen tier, in that order. A session that arrives at Welcome without a tier is sent back to Get Started to choose one.

The tier becomes the platform's own: a column on the tenant row, written through a narrow engine endpoint, and set once. A second call naming a different tier is refused, because a tier change is a billing event and billing does not exist yet.

Payment is out of scope, and the seam for it is the Launch button. When Stripe lands, Launch opens checkout instead of sign-up, and the tier is confirmed by a webhook rather than by the app. Nothing else in this flow needs to move.

## User Stories

### Choosing a tier

1. As a visitor, I want "Get started" to take me to a page where I choose a tier, so that I decide what I am signing up for before I have an account.
2. As a visitor, I want that page to show the same tiers, prices and credits as Pricing, so that I am never shown two sets of numbers.
3. As a visitor, I want its heading to ask me to choose rather than explain the pricing, so that I know I am being asked for a decision, not being sold to again.
4. As a visitor, I want the same questions answered on that page as on Pricing, so that a last doubt does not send me away to resolve it.
5. As a visitor, I want each tier's button to say "Launch", so that the action reads as committing rather than browsing.
6. As a visitor, I want Launch to take me to sign-up with my tier remembered, so that my choice survives creating the account.
7. As a visitor comparing prices, I want Pricing's tier buttons to work exactly as they do today, so that deciding on Pricing does not send me to a near-identical page to decide again.
8. As a visitor, I want that page to load as fast as the other public pages, so that the funnel step is not the slow one.
9. As a visitor on a phone, I want the page to stack without horizontal scroll, so that I can choose a tier wherever I heard about We-OS.
10. As a visitor, I want no trial, refund or cancellation promised anywhere on it, so that I am not misled about terms the product cannot yet honour.

### Signing up as a new business

11. As a new person, I want signing up to create my login and nothing else, so that no business is created in my name before I have said what it is.
12. As a new person, I want to be asked for my business name after I authenticate, so that the account I end up with is one I described.
13. As a new person who reached sign-up without choosing a tier, I want to be sent to Get Started to choose one, so that I cannot end up with an account whose tier is unknown.
14. As a new person who was already signed in when I chose a tier, I want Launch to take me to name my business rather than to a sign-up form, so that I am not asked to create an account I already have.
15. As a new person, I want my chosen tier recorded against my business, so that what I picked is what I have.
16. As a new person, I want to land on Home once my business exists, so that the next step — onboarding my Brand DNA — is in front of me.
17. As a new person whose business could not be recorded, I want to be told plainly and be able to try again, so that a transient failure does not cost me my account.
18. As a new person retrying after a failure, I want the retry not to create a second business, so that one attempt leaves one business.
19. As a new person who closed the tab partway, I want signing in again to bring me back to where I stopped, so that I am not stranded with a login and no business.
20. As a new person, I want the page where I name my business to be free of navigation I cannot use, so that I am not shown a product I have not entered yet.

### Being kept out until then

21. As the platform, I want a signed-in session with no business to be unable to reach Home, Campaigns, Calendar, Brand, Performance or Onboarding, so that the rule is enforced rather than suggested.
22. As the platform, I want a session with no business to reach only Welcome and Get Started, so that there is always a way forward and never a way around.
23. As the platform, I want a business whose tier was never recorded to be sent back to finish, so that the gap between creating a business and recording its tier cannot be lived in.
24. As a signed-in business owner, I want Welcome to send me to Home if I open it, so that a page for people without a business is not a page I can get stuck on.
25. As the platform, I want the engine to refuse a caller with no business regardless of how the request arrived, so that the redirect is a convenience and not the thing protecting tenant data.

### Returning and existing businesses

26. As an existing business owner, I want signing in to work exactly as it does today, so that this changes nothing for me.
27. As an existing business owner whose account predates tiers, I want a tier already recorded, so that I am not asked to choose one for an account I have been using for months.
28. As an existing business owner, I want my credits, campaigns and Brand DNA untouched, so that a change to how accounts are created does not reach my data.

### Maintainers

29. As a maintainer, I want the tier stored in our own database rather than only in the identity provider, so that a business rule about a tier can be written without asking a vendor.
30. As a maintainer, I want the tier settable once and never changed by the account holder, so that the endpoint is not a self-service upgrade the day tiers start to differ.
31. As a maintainer, I want the tier call safe to repeat, so that the retry the flow depends on is not itself a failure.
32. As a maintainer, I want an unknown tier name refused, so that the column holds one of three values and stays trustworthy when billing reads it.
33. As a maintainer, I want the tenantless session to have its own route group and layout, so that neither the public layout nor the app shell has to defend against a missing business.
34. As a maintainer, I want the browser suite to prove a session with no business is actually kept out, so that a future change that opens the gate fails a test rather than shipping.
35. As a maintainer, I want the tier names in the engine and in the web app to point at each other, so that renaming one is not a silent rejection at runtime.
36. As a maintainer, I want the tier's prices and credits to stay in exactly one place, so that the landing feature's single-source guarantee survives this one.
37. As a maintainer, I want the identity provider's configuration change written down in the setup steps, so that a fresh instance does not silently re-open the hole.
38. As a maintainer, I want the payment seam named explicitly, so that whoever adds Stripe knows which button becomes checkout and which rule becomes a webhook.

## Implementation Decisions

### The Get Started page

- **A separate public route**, in the public route group and the proxy's public matcher. Not a mode of Pricing: the two pages have different jobs — one is what you send a colleague, the other is the funnel step — and they will drift on purpose. It composes the existing tier-card and FAQ components, which is where the anti-drift guarantee already lives.
- **Composition**: a CTA heading and intro, the tier cards, the FAQ. No final-call section — the page *is* the call.
- **Copy**: the heading replaces Pricing's "The whole product, on every tier." with a line that asks for the decision. The landing feature's voice rules hold unchanged: no first-person "we", no promise the product cannot keep, no trial or refund language.
- **Generic CTAs repoint**: the top bar, hero and final-call "Get started" buttons lead to Get Started instead of sign-up. Their label stays "Get started" — the button and the page it opens agree.
- **Tier buttons say "Launch"** on both Pricing and Get Started. One component, one label, so the two pages cannot disagree.
- **Pricing's tier buttons keep their current destination** — sign-up, carrying the tier. Someone who decided on Pricing has already made the choice Get Started exists to extract; sending them to make it again is friction with no purpose.
- **Get Started's Launch buttons resolve their destination from the session**: signed out goes to sign-up with the tier; signed in with no business goes to Welcome with the tier. This page therefore reads the Clerk session but makes **no engine call**, so the public half's no-engine property (ADR-0012) holds.

### The tier, in the engine

- **A nullable tier column on the tenant row**, added by the schema module beside the existing guarded migrations. A guarded update backfills existing rows to the recommended tier, matching the style of the `allowance`→`credits` rename.
- **A tier-name literal in the engine's schemas**, carrying the three names and nothing else — no prices, no credit amounts. The literal and the web app's tier module each carry a comment naming the other, so whoever renames one finds the other.
- **A narrow endpoint, `PUT /tenant/tier`**, taking the tier in the body. The tenant comes from the verified claim and never from the body (ADR-0013). A general tenant-patch endpoint was rejected: there is one mutable field today, and a general shape invites questions — can the caller rename the business? change its credits? — that this feature has not answered.
- **Set-once semantics.** Setting a tier where none exists succeeds. Repeating the same tier succeeds and changes nothing, because the flow's retry depends on it. Naming a different tier than the one recorded is refused with **409** and a typed detail, alongside the engine's existing typed failures (402 for quota, 401 for authentication). When billing lands, a tier change arrives on a Stripe webhook, not on a call the account holder can make about their own subscription.
- **An unknown tier name is refused with 422**, so the column holds one of three values.
- **The tenant directory port grows the tier read and write**, and all three adapters implement it: Postgres, in-memory, and the passthrough adapter used by the filesystem layer, which holds no tier because it has no table to hold one in.
- **The tenant row is still minted implicitly** by the directory's resolve, on the first authenticated call. There is no create-tenant endpoint; the tier call is simply the first such call a new business makes. This is worth stating because it is easy to assume otherwise once a welcome flow exists.

### The welcome flow and the gate

- **Clerk's create-organization-on-sign-up is turned off.** This is a dashboard setting, outside the repository, and it is the one change that cannot be made in code. Missing it means Clerk creates the organization behind the app's back and the gate silently never fires — so it belongs in the web setup steps.
- **A third route group for the welcome page**, with its own minimal layout: brand mark, centered card, no navigation rail, no engine call. A tenantless session is genuinely a third state; the app shell reads the organization and the credits and would break for it, and the public layout would show a signed-in person a "Sign in" button.
- **The welcome page is a client component.** On submit it creates the Organization, activates it on the session, then calls a server action that records the tier, then redirects to Home. The ordering is forced: the Organization must exist before the session can carry an organization claim, and the session must carry that claim before the engine can mint the tenant the tier attaches to. Activation mutates the browser's session and cannot be done from the server, which is why the whole sequence lives on the client rather than being split.
- **A failure at the tier call** leaves the person on the page with the error and a retry. The Organization already exists, so the retry is the tier call alone — which is why that call must be safe to repeat.
- **Welcome with no tier redirects to Get Started.** Welcome with a business already active redirects to Home.
- **The proxy gate**: a signed-in session whose token carries no organization claim may reach only Welcome, Get Started and the public routes. Anything else in the app half redirects to Welcome. This is cheap — the claim is already in the token, so no engine call is needed on any request.
- **A tier check on Home's server load** redirects a tenant with no tier back to Welcome. One route, not every request. This closes the window between activating the Organization and recording the tier, which is the only state in the flow where a business exists without a tier.
- **The sign-up page reads its own tier parameter** and sets its post-authentication destination to Welcome carrying that tier, falling back to bare Welcome when absent — which then bounces to Get Started. Its sign-in fallback stays Home, because an existing person signing in from the sign-up form has a business and needs no welcome.
- **The redirect is a convenience, not the boundary.** The engine already refuses a token with no organization claim, and that remains what actually protects tenant data (ADR-0013). The gate exists so a person gets a way forward instead of a 401.

### Slicing

Three vertical slices, each leaving the app working:

1. **Get Started exists** — the new public page, the Launch rename, the generic CTAs repointed. Ships alone and changes nothing about authentication.
2. **The engine owns the tier** — column, backfill, literal, endpoint, port and adapters. Ships alone; nothing calls it yet.
3. **The welcome flow and the gate** — Clerk configuration off, the welcome route group, the proxy gate, the Home tier check, the session-aware Launch destinations. Blocked by 1 and 2, and cannot be split further: turning off Clerk's organization creation without the welcome page in place breaks sign-up outright.

## Testing Decisions

A good test here opens a page the way a person would, or calls the API the way a client would, and checks what they would see or get back. It does not inspect components, class names, middleware internals, or the shape of a server action. The seams below are the ones the codebase already uses; only one fixture is new.

### The engine's HTTP API — the default seam

The tier's whole contract is asserted through the FastAPI test client, which [the Brand DNA API tests](../../agent-harness/tests/test_brand_dna_api.py) name as the default seam for behaviour like this. Cases: setting a tier on a business that has none; repeating the same tier succeeding and changing nothing; a different tier refused with 409; an unknown name refused with 422; a caller with no organization claim refused with 401. Prior art for the authentication cases is the same file's unauthenticated-caller test.

### The tenant directory — the adapters, directly

The tier read and write are added to the existing [tenant directory tests](../../agent-harness/tests/test_tenant_directory.py), which already exercise all three adapters directly and then assert the API-level consequence. That file's shape is followed rather than a new one created.

### Postgres — the backfill

A test in the slow suite that the backfill sets the recommended tier on a row with no tier and leaves an already-set tier alone. It is marked slow like the rest of the Postgres suite, so `make test-postgres` is the run that proves it — a bare pytest skips it silently.

### Playwright — the flow, as a person

The gate and the welcome flow are a flow: nothing below the browser can prove that a session with no business cannot reach Home.

- **As a visitor**, in the existing public project: Get Started returns 200 and shows the three tiers with their prices and credits, the FAQ, and no final-call section; its tier buttons say "Launch" and carry the tier to sign-up; the top bar, hero and final-call buttons lead to Get Started; Pricing's buttons say "Launch" and keep their addresses; the existing voice and phone-width assertions run on the new page too; Welcome with no session redirects to sign-in.
- **As a tenantless session**, in a new project with a dedicated Clerk user who has no organization: Home redirects to Welcome; Campaigns redirects to Welcome; Welcome with no tier redirects to Get Started; naming a business at Welcome with a tier lands on Home. It runs with one worker, like the onboarding project, because it shares a mutable fixture. An `afterEach` deletes the Organization the spec created through Clerk's backend SDK, so the user is tenantless again for the next run — the same backend SDK the sign-in setup already uses.
- **As an existing business owner**, the existing signed-in projects are unchanged. Their users have organizations, and tiers after the backfill, so they never meet the gate — which is itself the assertion that nothing changes for an existing business.

### Unit — the one pure decision

The Launch destination resolver, tested beside the tier module as [its existing tests](../../web/src/lib/tiers.test.ts) are: signed out versus tenantless, with and without a tier. The pages themselves stay presentational and untested, per ADR-0012's gate.

### Deliberately not given a seam

The welcome page component (Playwright covers it as a person would), the proxy middleware in isolation (asserting it directly would test implementation; Playwright asserts where a person lands), and the server action (a thin call to the engine, whose behaviour the API seam already covers).

### Gates

`make check` and `make test-postgres` for the engine; TypeScript strict, ESLint, Prettier, vitest and the Playwright suite for the web. `/verify` in the running app before any slice is called done — the whole point is a flow, and green tests have never proved a flow works.

### A known fragility

The tenantless user stops being tenantless the moment the spec succeeds, so the project depends on its teardown. If that proves flaky, the fallback is to keep the redirect assertions — which create no Organization — and move the "naming a business lands on Home" case to a documented manual check.

## Out of Scope

- **Stripe, checkout, payment intents, subscriptions, invoices, or a paywall.** The Launch button is the seam they attach to; it opens sign-up today.
- Changing a tier once set: upgrade and downgrade flows, proration, or an admin tool for either.
- Enforcing different credit amounts per tier. The tier is recorded; credits still resolve exactly as they do today (ADR-0020).
- Deciding the real prices, credit amounts, or the cost-to-credit rate. The numbers stay placeholders in one module.
- Trials, refunds, cancellation terms, or any copy promising them.
- Multiple people per business, invitations, roles, or seats. One business, one person (ADR-0025).
- Any change to onboarding, the Questionnaire, the Brand DNA gate, or anything downstream of Home. A new business still lands on Home and goes to onboarding from there, unchanged.
- Renaming or restyling Pricing beyond the button label.
- Storing the tier in Clerk organization metadata. The platform row is the record; a metadata copy is a later optimisation if a cheaper gate is ever wanted.
- Analytics, funnel instrumentation, or conversion tracking on the new page.
- Deleting a business, or any account-closure flow.

## Further Notes

- The grilling that produced this PRD also wrote [ADR-0027](../../docs/adr/0027-the-platform-creates-the-tenant-and-owns-the-tier.md) and added **Get Started**, **Welcome** and **Tenantless Session** to [CONTEXT.md](../../CONTEXT.md), revising **Tier** to say where it is stored and that it is set once. Read those first.
- The landing PRD's line *"Nothing reads it yet; it is carried until billing exists"* is superseded: the tier parameter is now read at Welcome and recorded against the business.
- That PRD also recorded an open tension — the copy promises credits granted monthly and a move to a higher tier, while the engine has neither a monthly reset nor billing. This feature does not resolve it. It narrows it slightly: the tier is now recorded, so the "move to a higher tier" promise has something to move.
- Turning off Clerk's create-organization-on-sign-up is a **dashboard setting**, not a code change, and it is the single most likely thing to be missed when standing up a fresh Clerk instance. Missed, sign-up creates an organization behind the app's back and the gate never fires — with no error anywhere.
- When Stripe lands, the expected change is: Launch opens checkout; the tier is written by a webhook on payment success rather than by the welcome page; and the 409 on tier change is replaced by whatever the subscription lifecycle needs. The welcome page's organization creation should not need to move.

## Completion

- Completed: 2026-09-09
- Commits, on branch `tier-before-account`:
  - `9b8d758` Get Started: the page where a tier is chosen before an account exists
  - `75d8bec` The engine owns the tier: a column, a backfill, and PUT /tenant/tier
  - `02892c1` The gate, and the Welcome page that creates the business
  - `8cc55e2` Address code review: one set-once judgement, honest docstrings, real assertions
  - `6b3d4ec` Skip the tenantless project, saying why, until its Clerk user is provisioned
  - `77880c1` Glossary and ADR-0027: where Launch leads when signed in, and what guards the backfill
  - merged to main as `b6c878f` Merge: a tier is chosen before an account exists, and the platform creates the tenant
  - then `f1e281b` (merged as `6c07839`) and `d41b0cd` (merged as `68019a5`), which got the tenantless project running against the real Clerk instance
- Per-criterion evidence lives on the three archived issues in [issues/archive/](issues/archive/).
- Where the shipped flow departs from this document, on purpose: Home sends a business whose tier was never recorded to Get Started rather than to bare Welcome, and Welcome records the tier for a session that already has a business — the two rules as written would loop, since Welcome makes no engine call and cannot see the recorded tier. Recorded in CONTEXT.md and ADR-0027.
- Two Clerk dashboard settings turned out to be needed, and both are now named in the web setup steps: "Membership optional" (Personal Accounts on) in place of the default "Membership required", and "allow users to create organizations". The backfill is guarded on the column's absence rather than on empty values, so a later `init-db` never defaults a business mid-way through choosing.
- The open tension the landing PRD recorded stands: the copy promises monthly credits and a move to a higher tier, while the engine has no monthly reset and a tier change is refused until billing exists.
