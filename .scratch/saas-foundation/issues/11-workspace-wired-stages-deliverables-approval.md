# 11 — Workspace wired: stages, deliverables, approval

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0017](../../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md) · [ADR-0015](../../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md)

## What to build

The screen where the product actually happens: the business owner reads what the system produced and decides.

This resolves the stage-vocabulary mismatch that [ADR-0012](../../../docs/adr/0012-nextjs-frontend-and-bff-in-monolith.md) parked. The mockup's eight steps conflated two axes — five are stages that produce a deliverable, three (`Approve`, `Publish`, `Measure`) are lifecycle. The stepper now renders operator **Phases** grouping engine stages (`Strategy` covers brand-strategy and campaign-strategy; `Produce` covers creative-brief and asset-prompts), driven by the Phase each stage reports, while the campaign's lifecycle status renders as a separate indicator. The engine never adopts UI vocabulary and the interface never shows raw stage keys.

The workspace shows, for the selected stage: the **full deliverable content** — the API exposed only filenames and byte sizes until this work, so there was nothing to render — its version history with the feedback that produced each version, and whether it is Stale.

At an Approval Gate it presents the decision: approve, or send back with written feedback. Live run progress streams while a run is working.

End-to-end behaviour: open a campaign, watch a run progress through research, arrive at the brand-strategy gate, read the deliverable, send it back with feedback, watch version 2 arrive, compare it against version 1, approve it, and watch the run continue.

## Acceptance criteria

- [ ] The stepper renders operator Phases driven by the Phase each stage reports; no raw stage keys are shown.
- [ ] Campaign lifecycle status renders separately from stage progress.
- [ ] Full deliverable content renders for any stage that has produced one.
- [ ] Version history is browsable, showing the feedback that prompted each version.
- [ ] At an approval gate, approve and revise-with-feedback are both available and drive the real run.
- [ ] Approving visibly resumes the run; revising visibly produces a new version.
- [ ] Stale deliverables are clearly marked and offer an explicit re-run.
- [ ] Live run progress streams, and a closed and reopened tab reattaches to a run still in flight.
- [ ] Quota exhaustion and gate failure render as specific, actionable messages.
- [ ] Loading and error states exist for every engine call.
- [ ] The frontend smoke suite covers the approve and revise paths.
- [ ] Verified in the running app.

## Blocked by

- [07 — Approval gates: interrupt/resume and versioned revision](07-approval-gates-interrupt-resume-and-versioned-revision.md)

## Comments

**2026-09-03.** Two things this slice inherits from
[slice 10](archive/10-campaign-creation-wired.md).

**1. There is an interim workspace page to replace, not a blank one.**
`web/src/app/campaigns/[slug]/page.tsx` now has two branches. A *fixture* slug
(`fernway-refill-launch` and the other `campaignRows` entries) still renders the
old mockup workspace — stepper, StrategyDocument, decision rail — driven by the
`useDemoStore` client state. Any *real* slug renders `CampaignGoalDocument`, a
deliberately thin page showing the campaign's goal fields and a flat
phase/state list, loaded through the `loadCampaign` server action.

That second branch exists only because slice 10 had to stop a freshly created
campaign landing on "Campaign not found"; it is a placeholder, not a design.
This slice should delete **both** branches — the fixture path and the interim
goal page — along with the `useDemoStore` stage/approval state they lean on, and
render the real stages, deliverables and gate for every campaign. The engine
side it needs is already there: `GET /campaigns/{slug}` returns each stage with
its `phase`, `state`, `approval_policy`, `latest_version` and `stale` flag, and
`statusLabel`/`phaseLabel` in `web/src/lib/campaigns.ts` already map engine
lifecycle and stage keys to operator vocabulary (ADR-0017).

**2. "Verified in the running app" is not currently dischargeable.** The
Playwright suite cannot run without Clerk credentials and a seeded engine — see
[13](13-frontend-suite-cannot-run-without-credentials.md). Until that lands,
this slice's last two criteria can only be met at the engine boundary; do not
tick them on the strength of specs that were written but never executed. Slice
10 shows the failure mode: a spec asserting only `toHaveURL(...)` stayed green
over a workspace route that was broken for every real campaign.
