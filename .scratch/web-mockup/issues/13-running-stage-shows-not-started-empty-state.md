# 13 — A running stage's document pane says it is waiting on approvals it already has

Status: needs-triage
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
