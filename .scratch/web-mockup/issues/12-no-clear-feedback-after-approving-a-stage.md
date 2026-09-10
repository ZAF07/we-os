# 12 — After approving a stage, the user cannot tell that the run moved on or what runs next

Status: needs-triage
Type: bug

## Symptom

A tenant clicks **Approve** on a gated stage in a running campaign. The run does
resume automatically and correctly, but the UI does not tell the user that. The
user is left asking "did it move to the next stage?" with no answer on screen.

The feedback that exists today:

- The button disables and reads "Approving…" while the server action runs
  (`decision-panel.tsx:81-84`).
- The right rail keeps its pulsing dot and "Working" header
  (`run-progress.tsx:107-110`).
- A 1500 ms `router.refresh()` poll drives the page until the next gate
  (`workspace.tsx:141-145`).

Three gaps make that insufficient:

1. **The rail goes contentless right after the click.** Approving bumps
   `attempt` (`workspace.tsx:156`) to force the SSE stream to re-attach. The
   events reducer resets the list when `attempt` changes
   (`use-run-events.ts:66,84-86`), so `RunProgress` renders the "Working"
   header over an **empty list** until the trace replay lands. The single
   moment the user most needs reassurance is the moment the rail is blankest.
2. **Nothing ever names the next stage before it runs.** The prospective copy
   is generic — "Approving continues the run into the next stage."
   (`decision-panel.tsx:41-42`) and "You will be asked to approve each stage
   before the next one begins." (`workspace.tsx:469-470`). The next stage is
   named only retroactively, once `stage.start` arrives and the rail prints
   "Working on {title}." (`run-progress.tsx:18`).
3. **The Stages list does not reflect the move.** The now-running stage still
   reports `pending` and renders "Not started" — the same defect tracked in
   issue 11. So the list the user would naturally check for progress is
   unchanged before and after the approval.

There is also a related trap: once the user has clicked *any* stage in the nav
or stepper, `pickedKey` is set permanently and auto-follow is disabled for the
session (`workspace.tsx:64-71`, `web/src/lib/workspace.ts:170-176`). A user who
browsed stages before approving stays pinned on their picked stage and is never
moved to the next gate when it opens — so even the selected-stage highlight
stops tracking the run.

Expected: after approving, the user can see (a) that the approval was accepted
and the run resumed, (b) which stage is now running, (c) the status of every
other stage, and (d) ideally, before clicking, which stage the approval will
start.

Impact: no crash and no data loss — the pipeline behaves correctly. This is a
UI/UX defect in shipped code: the running system gives the user no readable
answer about its own state at a decision point.

## Repro

Deterministic; observed in the running app.

1. Start the stack and open a campaign workspace with a run in flight.
2. Wait for a stage to reach `awaiting_approval` and click **Approve**.
3. Watch the right rail and the left Stages list.

Observed: button reads "Approving…"; the rail shows "Working" over an empty
list for ~1-2 s; the Stages list is unchanged, with the newly-started stage
still labelled "Not started"; nothing names the stage that just began until its
`stage.start` event replays.

## Suspected location

- `web/src/components/workspace/decision-panel.tsx:41-42,79-85` — `ApprovalGate`;
  generic prospective copy, no next-stage name. `DecisionRail`
  (`workspace.tsx:422-450`) already receives the full `campaign`, so the next
  stage is derivable from stage order without new plumbing.
- `web/src/components/workspace/workspace.tsx:151-157` — the approve handler
  discards the engine response body (`{run_id, slug, stage, status:"running"}`)
  and reads only `result.error`; no optimistic update.
- `web/src/components/workspace/use-run-events.ts:66,82-86` — the `attempt`
  reset that empties the feed on re-attach.
- `web/src/components/workspace/run-progress.tsx:107-110` — "Working" header
  rendered over the empty list.
- `web/src/components/workspace/workspace.tsx:64-71` and
  `web/src/lib/workspace.ts:170-176` — `pickedKey` disabling auto-follow.
- Engine side (behaves correctly, listed for context):
  `agent-harness/src/marketing_os/entrypoints/api/app.py:1955-2047` and
  `agent-harness/src/marketing_os/graph/registry.py:256-297`.

## Relationship to other issues

Overlaps issue 11 (`11-running-stage-not-indicated-in-stage-nav.md`), which
covers the missing running-stage indicator in the Stages list generally. Gap 3
above is that same defect seen from the approval path. Consider fixing 11 first
— a correct running/next state in `StageNav` resolves a good part of this
issue, leaving the approval-moment feedback (gaps 1 and 2) as the remainder.
Triage may decide to merge the two.

## Open questions for triage

- Preserve the events feed across an `attempt` bump instead of clearing it, or
  render an explicit "Resuming…" placeholder for that window?
- Name the next stage prospectively on the Approve button/panel ("Approve —
  starts Performance plan"), or only after the fact?
- Should approving re-enable auto-follow (clear `pickedKey`) so the user is
  carried to the newly running stage?

## Acceptance criteria

- [ ] After clicking Approve, the UI confirms the approval was accepted and the
      run resumed — without a window showing a "Working" header over nothing.
- [ ] The stage that is now running is identifiable in the Stages list, and the
      other stages' statuses read correctly alongside it.
- [ ] Before approving, the user can see which stage the approval will start
      (or a decision not to do this is recorded on this issue).
- [ ] The behaviour is correct across a page reload during the post-approval
      window.
- [ ] A test covers the fixed behaviour (component/e2e as appropriate).
- [ ] `make check` passes, and `make test-e2e` passes (change touches `web/`).
