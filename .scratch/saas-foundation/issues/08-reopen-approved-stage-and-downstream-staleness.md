# 08 — Re-open an approved stage, and downstream staleness

Status: ready-for-agent
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

- [ ] An approved stage can be re-opened and revised.
- [ ] Re-opening a stage marks every downstream deliverable stale.
- [ ] Stale deliverables are **not** regenerated automatically, and no model call is made on their behalf.
- [ ] Staleness is exposed by the API and rendered distinctly in the interface.
- [ ] Stale stages can be re-run explicitly, and their flags clear on completion.
- [ ] Re-running a stale stage produces a new version rather than overwriting.
- [ ] A campaign with any stale deliverable cannot be treated as approved.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app.

## Blocked by

- [07 — Approval gates: interrupt/resume and versioned revision](07-approval-gates-interrupt-resume-and-versioned-revision.md)
