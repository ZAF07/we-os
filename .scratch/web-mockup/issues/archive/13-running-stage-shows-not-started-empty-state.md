# 13 — A running stage's document pane says it is waiting on approvals it already has

Status: completed
Type: bug

## Symptom

In the Workspace, when a run is executing a stage that has produced nothing
yet, opening that stage shows the empty state written for a stage the run has
not reached:

> Nothing produced yet. This stage runs once everything before it is approved.

Observed with the `test-two` campaign after Campaign strategy was approved:
Performance plan carried the running mark in the Stages list (pulsing dot,
"In progress"), the Plan phase chip was marked running, and the right rail's
`RunProgress` log read "Working on Brand strategy" through the live sequence —
yet the document pane claimed the stage was still waiting on upstream
approvals. The status pill above the title also read **"Not started"**.

This is a direct contradiction on one screen. The sentence states a
precondition ("runs once everything before it is approved") that is already
satisfied — everything upstream *is* approved, which is exactly why the run is
working on this stage. A user reading it reasonably concludes the run is stuck
or that their approval did not register.

Expected: while the run is working on the selected stage, the pane says so —
something like "This stage is running now. Its output appears here when it
finishes." The empty state that names the approval precondition belongs only to
stages the run has not started.

Impact: no crash, no data loss. The most reassuring moment in the flow (the
system is working on your approval) reads as the least — it tells the user the
opposite of what is true. Same surface and same class of defect as issues 11 and
12: the running state exists client-side but is not used where the user looks.

## Repro

Deterministic; observed in the running app (screenshot in the report).

1. Start the stack (`make e2e-up`) and open a campaign workspace.
2. Run the pipeline through to an approval — approve Campaign strategy so the
   run moves on to Performance plan.
3. While the Stages list shows Performance plan pulsing / "In progress", click
   Performance plan.

The pane shows the "Nothing produced yet…" empty state and a "Not started"
status pill, while the nav and right rail both show the stage running.

## Suspected location

- `web/src/components/workspace/workspace.tsx:455-459` — the empty state in
  `StageDocument`; branches only on `view.deliverable === null`, with no
  running case, so a running stage and an unreached stage render identically.
- `web/src/components/workspace/workspace.tsx:410-425` — `StageDocument`'s
  props; it is not passed `runningKey`, so it currently cannot tell the two
  apart. `StageNav` receives it (line 247) and already derives
  `running = stage.key === runningKey` (line 361) for exactly this purpose.
- `web/src/components/workspace/workspace.tsx:442` — the status pill, fed
  `stageStatus(stage.state)`; same omission, so it reads "Not started" on a
  running stage. `StageNav:362` already overrides the label to "In progress"
  when running.
- `web/src/components/workspace/workspace.tsx:108-109` — where `runningKey` is
  derived; the value is available at the `StageDocument` call site already.
- `web/src/lib/workspace.ts` — `stageStatus` status → label map; decide during
  diagnosis whether the running case belongs here (a shared helper both the nav
  and the document use) rather than being overridden at each call site.

## Existing tests that assert the current copy

Both assert the wrong-state string unconditionally and will need to move to a
not-yet-started stage, or gain a running-stage counterpart:

- `web/src/components/workspace/workspace.test.tsx:121`
- `web/tests/workspace.spec.ts:108`

## Notes

The engine's per-stage vocabulary (`pending | completed | awaiting_approval |
stale`) still has no `running` member — issue 11 resolved this by deriving the
running stage on the client from run events. Follow that same resolution here
rather than reopening the engine-side question.

## Acceptance criteria

- [x] While the run is working on the selected stage and it has produced
      nothing, the pane says the stage is running now, not that it waits on
      upstream approvals.
- [x] The status pill on that pane reads "In progress", not "Not started".
- [x] A stage the run has not reached keeps the approval-precondition copy
      and the "Not started" pill.
- [x] The running copy clears once the run leaves the stage.
- [x] The running state on the pane is derived client-side from run events,
      as issue 11 did — no engine change.
- [x] Tests cover the fixed behaviour; the two tests named above still hold
      or gained counterparts.
- [x] Web gates (unit, lint, typecheck, format) pass and `make test-e2e`
      passes.

## Comments

**2026-09-10 — diagnosis and fix** (branch `fix/running-stage-document-pane`)

Feedback loop: three vitest component tests in
`web/src/components/workspace/workspace-run.test.tsx` at the fake-EventSource
seam issue 11 built. Red on the exact symptom in ~3 s: after a `stage.start`
for Research, the pane's text was "Not startedResearch findingsNothing
produced yet. This stage runs once everything before it is approved."
Minimal repro: one `stage.start` event, the selected stage, an empty view.

Hypotheses, ranked: (1) `StageDocument` is never told which stage the run is
on, so it cannot branch — confirmed by the loop; (2) `stageStatus` has no
running case because the engine has none — true, but by design since issue
11, and the client already derives it; (3) the pane was stuck on "Loading…" —
ruled out by the received text.

Fix: `stageStatus(state, running)` owns the running case, so the Stages list
and the pane read it from one place; `StageDocument` takes `running` and its
empty state says "This stage is running now. Its output appears here when it
finishes." The `resuming` window after an approval is covered for free, since
`runningKey` already substitutes the expected stage there.

On the two tests the issue named: neither asserted the wrong state. Both
render with no run in flight, where the approval-precondition copy is right,
so they were left as they are and gained running-stage counterparts.

Code review (standards + spec) raised: `document` shadowed as a test
variable (renamed); the `running` default let a call site omit the mark
(now required); no pane test for the resume window (added); a stale stage
being re-run still offered a re-run above an "In progress" pill (banner now
hidden while running, with a test). Judged optional and left: a landmark
role on the pane so tests need not walk from the heading.

## Completion

- Completed: 2026-09-11
- Commit: a305d69 (fix) and 9ab2c19 (review follow-ups) on
  `fix/running-stage-document-pane`, merged to main with `--no-ff`.
- Evidence: five component tests in `workspace-run.test.tsx` ("the document
  pane of the stage a run is working on"), `stageStatus` unit test for the
  running flag, e2e approve test rules out the wrong sentence on the pane;
  web unit suite 141 passed, eslint/tsc/prettier clean, `make test-e2e`
  equivalent run from the branch: 73 passed (rebased on 54b9af6).
