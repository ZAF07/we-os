# Human approval gates, immutable deliverable versions, and downstream staleness

Each pipeline stage carries an **approval policy** — `auto` (advance when the QA reviewer passes it) or `human` (halt and wait for a person). Default gates: Brand Strategy, Campaign Strategy, Performance Plan, and always before asset generation; Research auto-advances. The graph reaches a gate via a LangGraph `interrupt()` and resumes on an explicit approve or revise call, so the run API gains `POST /runs/{id}/approve` and `POST /runs/{id}/revise {stage, feedback}` alongside the existing fire-and-forget start.

Revisions never overwrite. Each writes a **new deliverable version** carrying the feedback that prompted it, human or reviewer. Re-opening an already-approved stage marks every downstream deliverable **stale**, requiring an explicit re-run rather than silently regenerating them.

## Considered options

- **Run to completion, revise post-hoc** — rejected: it produces downstream work from unapproved upstream decisions, contradicting the documented constraint that creative assets are never generated before an *approved* strategy exists.
- **Human sign-off on every stage** — rejected as the default: maximum control, but six approvals per campaign is heavy friction for a solo founder wanting a first draft. The per-stage policy makes this a config change, not a rewrite.
- **Approve assets only, never strategy** — rejected: the strategy the assets rest on would never get a human yes.
- **Auto re-run downstream stages on re-open** — rejected: keeps the campaign always-consistent, but burns tokens and image-generation spend on work the user may not have wanted regenerated.
- **A stored `stale` flag per deliverable** — rejected: it must be written in the same breath as every re-run and every re-open, so it drifts from the version chain it describes. Staleness is derived instead: a deliverable is stale when its upstream's newest version was written after it.
- **Deriving staleness from `created_at`** — rejected as unsound. Wall-clock timestamps tie (microsecond resolution collides under rapid writes), and Postgres `now()` is fixed for a whole *transaction*, so two versions written together compare equal and the staleness silently vanishes — the precise failure the flag exists to prevent. Per-stage `version` numbers cannot substitute, since they say nothing about order *across* stages. Each version therefore carries a campaign-wide `sequence` assigned by the store.

## Consequences

- A durable checkpointer is a **hard prerequisite**, not a parallel chore: LangGraph cannot resume an interrupted run across a process boundary on `MemorySaver`. Postgres persistence ([ADR-0014](0014-postgres-system-of-record-and-split-governance.md)) must land first.
- The version chain gives the revision loop for creative assets ([ADR-0019](0019-creative-unit-is-the-approvable-asset.md)) for free, and yields an audit trail of *why* each decision changed — which is the product.
- The campaign gains an `awaiting_approval` lifecycle status ([ADR-0017](0017-stages-and-lifecycle-are-separate-axes.md)), and cannot read `approved` while any deliverable is stale.
- Re-opening a stage runs **that stage alone**, seeded with the owner's feedback and the deliverable they are reacting to — reusing the single-stage graph and the same state the Approval Gate's revise path already sets, so one seeding path serves both. It releases the caller's own gate-halted run, because re-opening an earlier decision is itself a decision about the pending one; a run that is actively executing is still refused.
