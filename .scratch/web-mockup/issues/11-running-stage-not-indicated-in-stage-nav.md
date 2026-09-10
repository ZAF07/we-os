# 11 — The stage a run is currently working on is not indicated in the Stages list

Status: needs-triage
Type: bug

## Symptom

While a campaign run is executing, nothing in the Workspace's left-hand
**Stages** list or in the top phase sequence shows which stage is running right
now. The only place the running stage is named is the right-hand rail's
`RunProgress` log ("Working on <stage>"), which is prose, not a state on the
stage list.

Two connected observations from the report:

1. The top sequence has no "Campaign strategy" chip — `brand-strategy` and
   `campaign-strategy` both carry `phase="Strategy"` and are deduped into one
   chip. Likewise `creative-brief` and `asset-prompts` collapse into one
   "Produce" chip. That collapsing is intended and stays, but it means the top
   row cannot be the place a user reads current progress.
2. The left Stages list, which does show every stage individually, styles only
   the *selected* stage (`bg-indigo-50` + bold) and a status dot. A running
   stage still reports `pending` from the engine, so it renders as a grey dot
   with the sub-label **"Not started"** — visually identical to a stage the run
   has not reached yet.

Expected: while a run is in flight, the stage being worked on is unambiguously
marked as running in the Stages list (and ideally reflected in the phase chip
that contains it), distinct from both "Not started" and "Selected".

Impact: no crash. The user cannot tell what the system is doing right now from
the primary progress UI — poor UI/UX on the main workspace screen.

## Repro

Deterministic; observed in the running app.

1. Start the stack (`make e2e-up`, or run the app normally).
2. Open a campaign workspace and start a run.
3. Watch the left **Stages** list while the run progresses.

Every stage that has not completed reads "Not started" with a grey dot,
including the one currently executing. Cross-check the right rail — it names
the running stage, so the information exists client-side but is not used by
`StageNav`.

## Suspected location

- `web/src/components/workspace/workspace.tsx:275-326` — `StageNav`; styles
  only `active = stage.key === selectedKey` plus a status dot.
- `web/src/lib/workspace.ts:34-39` — status → label map; `pending` → "Not
  started". No "running" case exists.
- `web/src/components/workspace/use-run-events.ts:5-10` — `stage.start` /
  `stage.done` events already carry the running stage key; currently consumed
  only by `RunProgress`.
- `web/src/components/workspace/run-progress.tsx:107-110` — the sole running
  indicator on the page today (pulsing dot + "Working").
- `agent-harness/src/marketing_os/campaign/progress.py:42-45` — per-stage state
  vocabulary is `pending | completed | awaiting_approval | stale`; there is no
  `running`. Decide during diagnosis whether to derive running state on the
  client from run events or add it to the engine's stage state.
- `web/src/components/workspace/workspace.tsx:185-196` + `web/src/lib/workspace.ts:101-119`
  — the phase chips and `toPhases` dedupe, if the running phase should also be
  marked.

## Related

Issue 12 (`12-no-clear-feedback-after-approving-a-stage.md`) covers the same
missing running-stage signal as seen from the approval path, plus the
approval-moment feedback gaps. Fixing this issue resolves part of that one.

## Open questions for triage

- Derive "running" client-side from `stage.start`/`stage.done` events, or add a
  `running` state to the engine's stage progress so a page reload is accurate
  too? (Events alone are lost on refresh mid-run.)
- Should the phase chip containing the running stage also carry an indicator?

## Acceptance criteria

- [ ] During an in-flight run, the executing stage is visibly distinguished in
      the left Stages list — not shown as "Not started".
- [ ] The running indicator is distinguishable from the *selected* stage
      highlight; a stage can be both at once and read correctly.
- [ ] The indication is correct after a page reload mid-run, or the decision
      not to support that is recorded on this issue.
- [ ] Stages that are genuinely pending, completed, awaiting approval, or stale
      keep their existing presentation.
- [ ] A test covers the fixed behaviour (component/e2e as appropriate).
- [ ] `make check` passes, and `make test-e2e` passes (change touches `web/`).
