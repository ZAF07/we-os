# 12 — Remaining screens wired to real data

Status: ready-for-agent
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

- [ ] No screen reads from mock fixtures; the client store no longer seeds demo data.
- [ ] Home's queue, counts and blocked list derive from real campaign state.
- [ ] Brand renders the tenant's Brand DNA and supports editing individual answers.
- [ ] Performance renders the Performance Plan's channels, spend allocation, placements and KPI tiers, and is explicit that these are planned, not measured.
- [ ] Calendar renders real campaign timeframes and stage milestones, with an honest empty state for unpublished work.
- [ ] Approving in the Workspace is reflected on Home and in the campaigns list without a manual refresh.
- [ ] Every screen has loading and error states, and refuses to render another tenant's data.
- [ ] The app remains usable below desktop width.
- [ ] The frontend smoke suite covers each screen against the real API.
- [ ] Verified in the running app.

## Blocked by

- [10 — Campaign creation wired to the engine](10-campaign-creation-wired.md)
- [11 — Workspace wired: stages, deliverables, approval](11-workspace-wired-stages-deliverables-approval.md)
