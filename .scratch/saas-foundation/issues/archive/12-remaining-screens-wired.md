# 12 — Remaining screens wired to real data

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md)

## What to build

The last of the mock fixtures come out. Home, Brand, Performance and Calendar render the tenant's real data, and the app becomes coherent end to end.

- **Home** — the decision queue built from campaigns actually awaiting approval, real counts, real blocked items with their reasons, and quota consumption. The engine side landed in slice 09: read `GET /usage`, which returns `used` / `allowance` / `remaining` / `exhausted` plus a per-campaign breakdown keyed by `slug`. Any operation that starts billable work — start a run, revise, re-open — can answer **402 `quota_exhausted`**, whose body carries `used` and `allowance`; surface its message rather than a generic error. This is the deferred half of slice 09's fourth acceptance criterion, so it belongs to this slice now.
- **Brand** — the tenant's Brand DNA as authored through the Questionnaire, editable per answer, with completeness clearly shown. This screen is why the DNA was renamed to align with it.
- **Performance** — whatever the Performance Plan deliverable actually contains: channel mix, per-channel spend allocation, Placements, and the three KPI tiers. It reports the *plan*, not measured results — no campaign has been published yet, and pretending otherwise would be fiction.
- **Calendar** — scheduled work as it genuinely exists at this stage. Publishing and scheduling arrive in a later PRD, so this screen shows planned campaign timeframes and stage milestones rather than fabricated post schedules.

Cross-screen coherence is part of the slice: approving in the Workspace updates the Home queue and the campaign's status, exactly as the mockup's client store used to fake.

Where a screen's designed content has no real data behind it yet, it shows an honest empty state naming what will fill it — not fixtures.

End-to-end behaviour: a business owner moves through every screen and sees only their own real data, with actions on one screen reflected on the others.

## Acceptance criteria

- [x] No screen reads from mock fixtures; the client store no longer seeds demo data.
- [x] Home's queue, counts and blocked list derive from real campaign state.
- [x] Brand renders the tenant's Brand DNA and supports editing individual answers.
- [x] Performance renders the Performance Plan's channels, spend allocation, placements and KPI tiers, and is explicit that these are planned, not measured.
- [x] Calendar renders real campaign timeframes and stage milestones, with an honest empty state for unpublished work.
- [x] Approving in the Workspace is reflected on Home and in the campaigns list without a manual refresh.
- [x] Every screen has loading and error states, and refuses to render another tenant's data.
- [x] The app remains usable below desktop width.
- [x] The frontend smoke suite covers each screen against the real API.
- [x] Verified in the running app.

## Blocked by

- [10 — Campaign creation wired to the engine](10-campaign-creation-wired.md)
- [11 — Workspace wired: stages, deliverables, approval](11-workspace-wired-stages-deliverables-approval.md)

## Comments

**2026-09-03.** **"Verified in the running app" and the smoke-suite criterion
are not currently dischargeable.** `pnpm test` in `web/` needs Clerk credentials
(`.env.local`, gitignored) plus a running engine holding an onboarded tenant —
see [13](13-frontend-suite-cannot-run-without-credentials.md). Specs for this
slice can be written but not executed until that lands, so verify at the engine
boundary and say so explicitly rather than ticking the criteria.

Also note, for the Brand screen: `GET /brand-dna/segments` was added in
[slice 10](archive/10-campaign-creation-wired.md) and is now declared in the
frozen contract. It returns just the Audience Segment names; the full authored
answers this screen edits still come from `GET /brand-dna`.

## Completion

- Completed: 2026-09-04
- Commits: `ebe0399` (implementation), `dac872c` (code review)

The comment above is **out of date** and was superseded by
[13](archive/13-frontend-suite-cannot-run-without-credentials.md): the browser
suite runs now, so the last two criteria were judged strictly rather than
deferred to the engine boundary.

| Criterion | Evidence |
| --- | --- |
| No screen reads fixtures; the store seeds no demo data | `mock-data.ts` and `store.ts` deleted; zero references remain; `zustand` removed from `package.json` |
| Home's queue, counts and blocked list derive from real state | `lib/home.ts` projects `GET /campaigns`; `home.spec.ts` creates a campaign, runs it to a gate, and finds it on the queue. **Deviation:** the queue and the blocked list are one list, tagged `Decision` or `Stale` — both are the owner's to act on and separating them would have split one decision across two panels. The distinction survives in the tag |
| Brand renders the DNA and edits individual answers | `brand-screen.tsx` over the published questionnaire; `brand.spec.ts` edits "Where do you serve customers?" and sees it saved |
| Performance renders the plan and is explicit it is planned, not measured | **Partial.** The "not measured" half is done and asserted — a spec checks the old invented metrics stay gone. The other half is weaker than the criterion reads: `lib/deliverable.ts` lays the plan out by whatever headings the specialist wrote, so channels, spend, placements and KPI tiers render *as sections* but are not identified individually. See [16](../16-performance-screen-does-not-identify-the-plans-parts.md) |
| Calendar renders timeframes and milestones, honest empty state | `calendar.spec.ts` creates a campaign and finds its timeframe; names per-post scheduling as what will fill it later |
| Approving is reflected on Home without a manual refresh | `changeCampaign` revalidates `/`, `/campaigns` and the workspace; `home.spec.ts` drives the whole loop in a browser |
| Loading and error states; no other tenant's data | `role="alert"` on all four; tenant isolation is structural — `engineFetch` sends only the Clerk token and the engine derives the tenant (ADR-0013), so no screen *can* ask for another's |
| Usable below desktop width | `smoke.spec.ts` asserts no horizontal overflow at 375px |
| Smoke suite covers each screen against the real API | Home 5, Brand 4, Performance 3, Calendar 3 — all green |
| Verified in the running app | `make test-e2e`: **40 passed, 0 failed, 2 skipped** — 42 specs in total, of which 2 are skipped |

### What code review caught

Two real gaps, both fixed:

1. **Quota refusals lost their numbers.** Only the `/usage` read was done; a
   402 on a run fell through to the bare message without `used`/`allowance`.
2. **Performance was a shortcut** — raw markdown with `##` and `**` visible,
   rather than the channels, spend and KPI tiers the issue asked for.

Plus a vocabulary slip worth recording: Home counted **raw engine statuses**
(`awaiting_approval` on screen), and the queue's second tag said "Blocked" — a
fourth synonym for what CONTEXT.md defines as **Stale**, which is what its
_Avoid_ list exists to prevent.

### A test that was wrong, not the product

The first coherence spec asserted that approving clears the campaign from Home's
queue. It does not, and should not: approving brand-strategy advances to
campaign-strategy, which is *also* a human gate, so the campaign is still
waiting and belongs on the queue. Confirmed at the engine before changing
anything — the test was rewritten, not the behaviour.

### Corrected after a second review

The evidence table above was rewritten once. As first written it claimed the
Performance criterion outright, said Home had 6 specs when it has 5, and did not
record that the blocked list had been folded into the queue. A completion note
that overstates is its own defect — it is the thing a future reader trusts
instead of re-deriving — so the corrections are recorded here rather than made
silently.

A second review pass also found and fixed: two screens still carrying the
duplicated engine-unreachable string the first pass was supposed to have
removed; a dead `/workspace` route still in the nav, pointing at a hardcoded
`acme` slug no tenant owns; and an ordering bug where a 402 carrying
`missing_fields` would have rendered the gate message instead of the quota one.
`refusalMessage` now has six unit tests, including that ordering.

### Still open

Two onboarding specs stay skipped, each saying why in the file: both need a
tenant with **no** Brand DNA, and the e2e stack seeds a complete one because
every other spec needs a tenant that can create campaigns. Worth its own issue
if onboarding regressions start slipping through.

Also noted during review: test campaigns accumulate in the shared seeded tenant
across runs, so specs asserting on a campaign *name* rather than its slug get
flakier over time. The specs here assert on slugs for that reason.
