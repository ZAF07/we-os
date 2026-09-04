# 11 — Workspace wired: stages, deliverables, approval

Status: completed
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

- [x] The stepper renders operator Phases driven by the Phase each stage reports; no raw stage keys are shown.
- [x] Campaign lifecycle status renders separately from stage progress.
- [x] Full deliverable content renders for any stage that has produced one.
- [x] Version history is browsable, showing the feedback that prompted each version.
- [x] At an approval gate, approve and revise-with-feedback are both available and drive the real run.
- [x] Approving visibly resumes the run; revising visibly produces a new version.
- [x] Stale deliverables are clearly marked and offer an explicit re-run.
- [x] Live run progress streams, and a closed and reopened tab reattaches to a run still in flight.
- [x] Quota exhaustion and gate failure render as specific, actionable messages.
- [x] Loading and error states exist for every engine call.
- [x] The frontend smoke suite covers the approve and revise paths.
- [x] Verified in the running app.

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

## Completion

- Completed: 2026-09-04
- Commits: `b0e921f` (implementation), `4fd872b` (code review), `16cd7a1` (browser verification + three defects it caught)

Every criterion verified against the running app, not only at the engine
boundary — the e2e stack landed with issue 13, so "verified in the running app"
means what it says.

| Criterion | Evidence |
| --- | --- |
| Stepper renders Phases, no raw stage keys | Browser snapshot: `1 Research` / `2 Strategy` / `3 Plan` / `4 Produce` from six engine stages. `workspace.spec.ts` "renders its Phases and stages" + "shows no raw engine stage keys" |
| Lifecycle separate from stage progress | `Ready for review` pill beside per-stage `Approved` / `Not started`. `workspace.spec.ts:85` |
| Full deliverable content renders | `article "Deliverable"` carrying the whole markdown. `workspace.spec.ts:153` asserts it is non-empty |
| Version history with the feedback behind each version | `v2` + "You asked: Too premium; we are mid-market." `workspace.spec.ts:165` |
| Approve and revise both available, driving the real run | Both buttons under "Decision required"; engine log shows the resume and `version=2` |
| Approving resumes; revising produces a new version | `workspace.spec.ts:139` and `:165`, both green |
| Stale marked, explicit re-run offered | `workspace.tsx:365` renders `StaleBanner`; re-run is **stage-scoped** (fixed in review — it ran the whole pipeline), pinned by `test_workspace_contract.py` |
| Live progress streams; a reopened tab reattaches | Browser log shows the streamed feed; the engine replays a trace from the top (`app.py:1970`), pinned by `test_workspace_contract.py` |
| Quota and gate failure are specific and actionable | `engineMessage` surfaces the engine's own wording and appends the gate's `missing_fields`; the refusal is pinned to carry them |
| Loading and error states on every engine call | `Loading…`, `Loading version…`, `role="alert"` on stage-load failure, action failure, and engine-unreachable |
| Smoke suite covers approve and revise | Both specs green in a real browser, no longer skipped |
| Verified in the running app | `make test-e2e`: **36 passed, 0 failed, 3 skipped** |

### What browser verification caught that the engine boundary could not

Three defects, all invisible to an API-level test:

1. **The selected stage never followed the run.** Chosen once on mount, so a run
   reaching a gate left the person on the draft's stage with no Approve button.
2. **A stage that produced a deliverable mid-session kept reading "Nothing
   produced yet"** — the load effect ignored the newest version.
3. **Revising never showed the new version.** A revise resumes the *same* run,
   whose stream had already closed at the first gate, so nothing told the page
   v2 had landed.

This is the case for the suite existing, and the answer to slice 10's failure
mode.

### Skipped specs, and why

Three, each with the reason in the file: two onboarding specs need their own
unseeded tenant (the stack seeds a *complete* Brand DNA, which every other spec
needs), and Home's queue CTA points at fixture campaigns until [12](../12-remaining-screens-wired.md)
wires it to real data. None is a workspace behaviour.
