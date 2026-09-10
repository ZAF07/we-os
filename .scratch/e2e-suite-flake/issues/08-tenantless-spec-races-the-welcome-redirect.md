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

**2026-09-10 — diagnosis confirmed (`/diagnosing-bugs`), on branch
`fix/tenantless-spec-passthrough-assert`.**

Feedback loop: a throwaway spec (`web/tests/probe-tenantless.spec.ts`, deleted
before the gate ran) walked the same steps as this spec against the gate's own
stack (`web-built`, the production build) while recording every main-frame
navigation and app request with a timestamp, then ran the suspect assertion in
a try/catch and reported its verdict next to how long the page actually sat on
`/welcome?tier=strategist`.

What the timeline shows, every run: the click's request for Welcome's payload
answers in about 2 ms; the address flips about 13 ms after the mouse event; the
tier action (`POST`) takes about 15 ms and the `/home` payload about 7 ms; the
address becomes `/home` 43–78 ms after it became `/welcome?tier=strategist`.
The pass-through is real, and it is that short.

Why the assertion can miss it: with a string argument, `expect(page).toHaveURL()`
is not event-driven. It is `toMatchText` over `frame._expect("to.have.url")`,
which samples `location.href` on Playwright's backoff — gaps of 0, 20, 50,
100, 100, then 500 ms (`retryWithProgressAndBackoff`, playwright-core 1.61.1)
— and each sample also waits for the page's main thread. A 50–75 ms window
that opens and closes between two samples is never seen, and the later it
opens, the wider the gaps it has to fall between. Load does exactly that: it
delays Welcome's payload and the browser's commit without lengthening the
pass-through, which is bounded by two fast server calls. Only the predicate
and URLPattern forms of `toHaveURL` use the event-driven `waitForURL`.

Hypotheses, ranked before testing, and what happened to each:

1. Sampling misses a transient — **confirmed.** Holding only the GET for
   Welcome's payload 300 ms (`page.route`; the `POST` untouched) made the
   original assertion fail 5/5 with the gate's exact log shape: 14 samples in
   5 s, `5 × unexpected value ".../get-started"` then `9 × ".../home"` (the
   gate saw `2 + 12`), while the recorder still saw `/welcome?tier=strategist`
   for 57–75 ms in each run.
2. The browser never visits `/welcome?tier=strategist` because Next coalesces
   the push and the replace — falsified: the navigation event is in every
   timeline, failing runs included.
3. The session token expired and the action was refused (the cause fixed in
   `773e464`) — falsified: the failing run observed `/home`, and no sign-in
   address appears anywhere.
4. Launch's `href` differs for a session that already has a business —
   falsified: `launchHref` depends on signed-in only, and the timeline shows
   the `/welcome?tier=strategist` request and navigation.
5. `toHaveURL` is event-driven, so something else is wrong — falsified by the
   source, as above.

Baseline without the delay: 15/15 passed (5 plain, 10 with the link hovered
500 ms before the click), which is the "passes in isolation" of the symptom.

Fix: assert the tier on the link's `href` before the click, drop the
pass-through assertion, keep the landing on `/home` and the Home heading.
Under the same 300 ms delay the fixed assertion passed 5/5. No sibling spec
asserts a pass-through: every other `toHaveURL` in `web/tests` follows a
`goto` or a click to a destination that stays.
