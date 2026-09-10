# 12 — After approving a stage, the user cannot tell that the run moved on or what runs next

Status: completed
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

- [x] After clicking Approve, the UI confirms the approval was accepted and the
      run resumed — without a window showing a "Working" header over nothing.
- [x] The stage that is now running is identifiable in the Stages list, and the
      other stages' statuses read correctly alongside it.
- [x] Before approving, the user can see which stage the approval will start
      (or a decision not to do this is recorded on this issue).
- [x] The behaviour is correct across a page reload during the post-approval
      window.
- [x] A test covers the fixed behaviour (component/e2e as appropriate).
- [x] `make check` passes, and `make test-e2e` passes (change touches `web/`).

## Comments

**2026-09-10 — diagnosis (branch `workspace-running-stage-feedback`)**

Feedback loops:
- Same vitest component test as issue 11 (`workspace-run.test.tsx`): approve
  at the brand-strategy gate, then assert the rail and Stages list. Red on the
  exact symptom — the rail read "Working" over an empty list.
- An engine test at the trace tailer seam
  (`agent-harness/tests/test_observability.py`): a trace holding a gate
  summary followed by the resumed run's events. Red — the tailer stopped at
  the gate summary and never yielded the resumed events.

Causes, confirmed by the loops:
1. **Engine (the deeper one, not in the original report):** a resumed run
   appends to the same trace, whose halt wrote a terminal
   `run.summary outcome=awaiting_approval`. `tail_trace` closed on the first
   summary it replayed, so a re-attached stream — and any reload after an
   approval — ended at the halt. The rail could never narrate the resumed run.
   This is why "nothing names the stage that just began until its
   `stage.start` replays": it never replayed.
2. The events hook returned an empty feed while `attempt` had changed and the
   stream had not replayed yet.
3. `ApprovalGate` was never told which stage the approval starts.
4. `pickedKey` was never cleared, so a person who had browsed stayed pinned.

Decisions:
- Tailer: a summary whose outcome is `awaiting_approval` ends a segment, not
  the trace. Liveness decides — a halted run is not live, so the stream still
  drains and closes at the gate; a resumed run is live, so the tailer reads
  through the gate summary.
- Hook: keeps the prior feed across a resume, flagged `resuming`, and reports
  a gate halt as `halted` rather than `finished`. The rail header reads
  "Waiting for your decision" at a gate instead of "Run finished".
- The panel names the next stage prospectively: "Approving starts
  Performance plan." (or "this is the last stage").
- Approving and revising clear the pick, so the Workspace follows the run to
  the next gate. Re-opening does not — it is not a decision at a gate.
- The stage a decision sets going is shown as running from the moment the
  decision is accepted until the stream replays; then the stream wins.

**2026-09-10 — code review (`/code-review` against main)**

Spec review found three real defects in the first cut, all fixed:
1. The optimistic running mark was set only by approve/revise and never
   cleared, so a later re-run or re-open would briefly show the stage the
   *last approval* started. Now every action that resumes or starts a run
   names the stage it sets going (re-run and re-open name their own stage;
   start names none).
2. If the re-attached stream errored before its first message, the hook
   carried the gate's `halted` flag forward and the rail read "Waiting for
   your decision" while the run was in fact working. The error path now only
   trusts flags from the same attachment; otherwise it reports the feed lost.
3. During the replay after a decision, `resuming` dropped on the first
   replayed event, so the list briefly tracked the *old* events (including
   the old gate summary — a header flicker and a spare refresh). The hook now
   keeps the prior feed until the replay has got past it.

Tests added for each, plus a reload-after-approval replay test (acceptance
criterion "correct across a page reload during the post-approval window",
which previously had only the engine-seam test).

Standards: see issue 11's comment.

## Completion

- Completed: 2026-09-10
- Commits: 6a214ed (the fix), a7cb680 (code-review fixes)

Evidence per criterion:
- Approval confirmed, no "Working" over nothing — "keeps the progress feed on
  screen and marks the next stage as started" in
  `web/src/components/workspace/workspace-run.test.tsx`: the rail keeps its
  lines through the re-attach and the replay; the browser spec asserts the
  replayed "You approved Brand strategy." line.
- Running stage identifiable, others correct — same test, plus "marks the
  stage a re-run sets going, not the one a past approval did".
- Next stage named before approving — "names the stage the approval will
  start, before the click"; `web/tests/workspace.spec.ts` asserts "Approving
  starts Campaign strategy." and, at the next gate, "…Performance plan.".
- Correct across a reload in the post-approval window — the tailer now reads
  through a gate summary (`test_tail_trace_replays_past_a_gate_summary_when_the_run_was_resumed`,
  `…follows_a_live_run_through_its_gate_summary`), and "is read correctly by a
  page reloaded after an approval" covers the page.
- Tests — the above; the browser spec "approving a stage resumes the run into
  the next one" verifies the whole path in the running app (production build).
- Gates — `make check` (658 passed, 111 skipped), `make test-postgres` (769
  passed), `make test-e2e` 73 passed after each commit; web `pnpm test:unit`
  135 passed, lint, typecheck and format:check clean.
