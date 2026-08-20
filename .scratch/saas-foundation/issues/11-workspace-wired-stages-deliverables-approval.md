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
