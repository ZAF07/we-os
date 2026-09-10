# 08 — The tenantless Launch spec races the Welcome redirect

Status: ready-for-agent
Type: bug

## Symptom

`make test-e2e` fails one spec under full parallel load:

```
[chromium-tenantless] › tests/tenantless.spec.ts:129:5 ›
  a business whose tier was never recorded is sent from Home to choose,
  and Launch finishes it

Expect "toHaveURL" with timeout 5000ms
  2 × unexpected value "http://localhost:3100/get-started"
  12 × unexpected value "http://localhost:3100/home"
  at web/tests/tenantless.spec.ts:154:22
```

1 failed, 1 did not run, 71 passed (1.4m).

Run in isolation against the same stack it passes 3/3
(`pnpm exec playwright test --project=chromium-tenantless --repeat-each=3
-g "tier was never recorded"` → 4 passed). Load-sensitive, not deterministic.

## Diagnosis

The product is behaving correctly. The assertion is wrong.

[web/tests/tenantless.spec.ts:154](../../../web/tests/tenantless.spec.ts#L154)
asserts the URL *equals* `/welcome?tier=strategist`:

```ts
await expect(page).toHaveURL("/welcome?tier=strategist");
await expect(page).toHaveURL("/home", { timeout: 60_000 });
```

But `/welcome` with a tier and an existing business is a **pass-through**, not
a destination. Per the docstring on
[web/src/app/(welcome)/welcome/page.tsx](<../../../web/src/app/(welcome)/welcome/page.tsx>):

> That second path is how a business whose tier was never recorded finishes:
> Home sends it to choose, and Launch brings it back here with the choice.

The form records the tier and continues to `/home`. Line 154 is trying to catch
a transient stop mid-redirect within 5s. The failure log proves the app did the
right thing — it observed `/home`, 12 times.

Line 155 (`/home`) and line 156 (the Home heading) already assert the outcome
that matters, so line 154 adds no coverage the spec doesn't already have.

## Why it surfaced now

The tenantless project was **skipped** when this spec was written
(`02892c1`, 2026-09-09) and when issue `tier-before-account/03` was verified —
that verification records "6 skipped (the tenantless project, which waits on a
provisioned user)". `6b3d4ec` made the skip conditional on
`E2E_CLERK_TENANTLESS_USER_EMAIL`. The Clerk user has since been provisioned,
so the project now runs and this assertion is failing on its first real
exercise. It never passed under load; it was simply never run.

This is distinct from the five flake causes fixed in `773e464` — those were
infrastructure (route compile, Turbopack cache, sleep, token expiry,
hydration). This one is a single bad assertion.

## Fix

Drop the intermediate-URL assertion at line 154. Keep 155 and 156.

If the intent was to prove Launch carries the tier in the query string, assert
that on the link's `href` before the click (the spec already does exactly this
for every tier at lines ~120-126) rather than on the post-click URL.

Check the sibling specs in the same file for the same pattern.

## Acceptance criteria

- [ ] `tenantless.spec.ts:129` no longer asserts an intermediate redirect URL as a destination.
- [ ] The spec still proves Launch carries the chosen tier, and still asserts the landing on `/home` with the Home heading.
- [ ] Any sibling spec asserting a pass-through URL is corrected the same way.
- [ ] `make test-e2e` passes end to end, including the `chromium-tenantless` project.

## Comments

**2026-09-10.** Found by `/post-implement` while closing out the
`saas-foundation` PRD. It does not block that close-out: the PRD's deliverable
(the tenantless gate and Welcome flow) is implemented and works — the defect is
in the test's assertion, not the product.
