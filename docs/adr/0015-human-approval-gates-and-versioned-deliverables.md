# Human approval gates, immutable deliverable versions, and downstream staleness

Each pipeline stage carries an **approval policy** — `auto` (advance when the QA reviewer passes it) or `human` (halt and wait for a person). Default gates: Brand Strategy, Campaign Strategy, Performance Plan, and always before asset generation; Research auto-advances. The graph reaches a gate via a LangGraph `interrupt()` and resumes on an explicit approve or revise call, so the run API gains `POST /runs/{id}/approve` and `POST /runs/{id}/revise {stage, feedback}` alongside the existing fire-and-forget start.

Revisions never overwrite. Each writes a **new deliverable version** carrying the feedback that prompted it, human or reviewer. Re-opening an already-approved stage marks every downstream deliverable **stale**, requiring an explicit re-run rather than silently regenerating them.

## Considered options

- **Run to completion, revise post-hoc** — rejected: it produces downstream work from unapproved upstream decisions, contradicting the documented constraint that creative assets are never generated before an *approved* strategy exists.
- **Human sign-off on every stage** — rejected as the default: maximum control, but six approvals per campaign is heavy friction for a solo founder wanting a first draft. The per-stage policy makes this a config change, not a rewrite.
- **Approve assets only, never strategy** — rejected: the strategy the assets rest on would never get a human yes.
- **Auto re-run downstream stages on re-open** — rejected: keeps the campaign always-consistent, but burns tokens and image-generation spend on work the user may not have wanted regenerated.

## Consequences

- A durable checkpointer is a **hard prerequisite**, not a parallel chore: LangGraph cannot resume an interrupted run across a process boundary on `MemorySaver`. Postgres persistence ([ADR-0014](0014-postgres-system-of-record-and-split-governance.md)) must land first.
- The version chain gives the revision loop for creative assets ([ADR-0019](0019-creative-unit-is-the-approvable-asset.md)) for free, and yields an audit trail of *why* each decision changed — which is the product.
- The campaign gains an `awaiting_approval` lifecycle status ([ADR-0017](0017-stages-and-lifecycle-are-separate-axes.md)).
