# 13 — The frontend Playwright suite cannot be run locally, so "verified in the running app" is unprovable

Status: needs-triage
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md)

## What's wrong

Every wired-frontend slice carries two acceptance criteria that cannot currently
be discharged on a clean checkout:

- "The frontend smoke suite covers …"
- "Verified in the running app."

Running `pnpm test` in `web/` needs two things the repository does not provide:

1. **Clerk credentials.** `web/playwright.config.ts` loads `.env.local` then
   `.env`, and `tests/auth.setup.ts` signs in once so `clerkMiddleware` lets the
   suite reach any application route. Only `web/.env.local.example` is committed
   (`.env.local` is gitignored, correctly — it holds real keys), so with no
   `.env.local` the `setup` project fails and every spec is blocked.
2. **A running engine** holding the tenant whose Brand DNA the specs read. The
   campaign specs pick an Audience Segment from the radiogroup that
   `GET /brand-dna/segments` fills, so they need an engine with an onboarded
   tenant, not just a Next server.

The consequence is that specs can be *written* but never *run* here. Slice 10's
suite was authored and left unexecuted; [11](11-workspace-wired-stages-deliverables-approval.md)
and [12](12-remaining-screens-wired.md) carry the identical criteria and will hit
the identical wall.

This already cost something real. In slice 10 the create-campaign spec asserted
only `toHaveURL(...)` and not that the page rendered, so it stayed green over a
workspace route that answered "Campaign not found" for every real campaign. The
defect was caught by code review, not by the suite — precisely because the suite
does not run.

## What's needed

A documented, repeatable way to run the frontend suite end to end. Decide and
record:

- Where the test Clerk credentials come from (a shared test instance, a seeded
  dev instance, or Clerk's testing tokens) and how a developer obtains them.
- How the engine and its onboarded test tenant are brought up for a suite run —
  and whether the suite should own that lifecycle (`webServer`-style) rather
  than assuming a server is already listening.
- Whether CI runs this suite, and if so with which secrets.
- Whether the seeded tenant's Brand DNA is fixture-controlled, so a spec can
  assert on a *known* segment instead of "whatever the first radio happens to be".

Until this lands, treat "Verified in the running app" on any frontend slice as
verified **at the engine boundary only**, and say so explicitly rather than
ticking it.

## Acceptance criteria

- [ ] A documented command brings up whatever the suite needs and runs `pnpm test` green from a clean checkout.
- [ ] The credential path is documented in `web/README.md` (or `USAGE.md`) with no real keys committed.
- [ ] The test tenant's Brand DNA is seeded deterministically, so specs assert on known segments.
- [ ] The slice-10 specs (`new-campaign.spec.ts`, `campaigns.spec.ts`, the create-campaign case in `smoke.spec.ts`) are confirmed passing, not merely written.
- [ ] CI's position is decided and recorded — either the suite runs there, or the issue says why it does not.

## Comments

**2026-09-03.** Filed while closing out
[slice 10](archive/10-campaign-creation-wired.md). Slice 10's engine behaviour
*was* verified end to end against a real running engine and the real tenant
(creation, DNA Gate pass, run start returning 202, per-field 422s, an invented
segment refused, slug collision to `-2`, archive removing a campaign from the
list while it stays readable, 404s for unknown slugs). What could not be
exercised is the browser: the wizard, the list, and the archive button were
never driven by a real user agent.
