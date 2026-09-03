# 08 — Re-open an approved stage, and downstream staleness

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0015](../../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md)

## What to build

Campaigns get edited weeks later, after work has been built on top of them. This slice makes that safe.

A business owner can re-open a stage they previously approved and revise it. Doing so marks **every downstream deliverable Stale** — not regenerated. Stale work is clearly flagged, and the owner re-runs the stale stages explicitly when they are ready.

The alternative — auto-re-running everything downstream — was rejected: it keeps the campaign consistent, but burns tokens (and later, image-generation spend) on work the owner may not have wanted regenerated. Staleness makes the inconsistency **visible and the owner's to resolve**, which is the same principle as the approval gates themselves.

The failure this prevents is quiet and expensive: creative resting on a strategy that was superseded, with nothing in the interface saying so.

End-to-end behaviour: complete a campaign through the creative brief, go back and revise the approved brand strategy, and see the campaign strategy, performance plan and creative brief all marked stale with a clear prompt to re-run; re-run them and the flags clear.

## Acceptance criteria

- [x] An approved stage can be re-opened and revised.
- [x] Re-opening a stage marks every downstream deliverable stale.
- [x] Stale deliverables are **not** regenerated automatically, and no model call is made on their behalf.
- [x] Staleness is exposed by the API and rendered distinctly in the interface.
- [x] Stale stages can be re-run explicitly, and their flags clear on completion.
- [x] Re-running a stale stage produces a new version rather than overwriting.
- [x] A campaign with any stale deliverable cannot be treated as approved.
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [x] Verified in the running app.

## Blocked by

- [07 — Approval gates: interrupt/resume and versioned revision](07-approval-gates-interrupt-resume-and-versioned-revision.md)

## Comments

- **Staleness is derived, not stored.** A deliverable is stale when an upstream
  stage's newest version was written after it, read off the version chain
  (`governance/staleness.py`). No column to keep in sync with every re-run, so
  the flag cannot drift from the versions it describes.
- **Ordering is a campaign-wide `sequence`, not `created_at`.** The first cut
  compared timestamps; code review caught that this silently loses staleness.
  `now_timestamp()` collides ~16% of the time under rapid writes (measured: 1685
  distinct of 2000), and Postgres `now()` is fixed for a whole *transaction*, so
  two versions written together tie and downstream work reads as fresh. Version
  numbers cannot substitute — they count within one stage, so they cannot order
  events across stages. `DeliverableVersion.sequence` (a `bigserial` in Postgres,
  derived in the local adapters) is assigned by the store instead. Regression
  test: `test_staleness_holds_when_every_version_shares_one_timestamp`, proven
  red on the old derivation and green on the new one.
- **Re-open = a single-stage run seeded with the owner's feedback.** It reuses the
  existing single-stage graph and the `human_feedback` state key an Approval Gate
  refusal already sets, so one seeding path serves both. `_previous_draft` reads
  the saved deliverable when state carries none, which is what makes re-opening a
  revision of existing work rather than a rewrite from scratch.
- **Re-opening releases the caller's own gate-halted run** (`_release_gate_held_by`).
  Not in the issue, but required: without it a re-open is refused with
  `run_conflict` whenever a gate is holding, which is the common case. Re-opening
  an earlier decision *is* a decision about the pending one. Scoped to the
  caller's own halted run — an actively-executing run is still refused.
- **Lifecycle status now reported on `GET /campaigns/{slug}/stages`** as the
  vehicle for "cannot be treated as approved": `approved` requires every stage
  produced *and* none stale. Derived from the deliverables, not from the rendered
  state strings, so lifecycle cannot drift via a presentation change. A full
  `GET /campaigns/{slug}` belongs to issue 10.
- **Contract extended** with `reopenStage`, plus `stale`/`latest_version` on
  `Stage` (which the code already returned — the schema had drifted). Spectral
  clean.
- **Frontend scope was an explicit decision**: the demo shell renders the stale
  visual language (orange `Stale` pill, banner carrying the "Re-run this stage"
  action that clears it, stage-nav dot and subtitle) driven by the mock store.
  Issues 10–12 wire it to real engine data. Chosen over deferring all UI so the
  visual language exists first.
- Pre-existing, unrelated to this slice: `contracts` `npm test` cannot start
  Prism locally, and 4 onboarding Playwright tests need a live engine. Both fail
  identically on a clean tree.

## Completion

- Completed: 2026-09-03
- Commit: <to be filled in manually>
