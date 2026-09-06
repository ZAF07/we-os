# 04 — Lift campaign progress out of the HTTP adapter

Status: completed
Type: task

## Parent

[ADR-0017](../../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md) · [ADR-0001](../../../docs/adr/0001-ports-and-adapters-architecture.md) · best done after [02](02-postgres-only-in-production.md)

## Why

"Where has this campaign got to?" is the question the product exists to answer,
and it is answered by four private functions inside the HTTP module:

- `entrypoints/api/app.py:880` `_stage_report`
- `entrypoints/api/app.py:1244` `_campaign_status`
- `entrypoints/api/app.py:1277` `_stage_awaiting_approval`
- `entrypoints/api/app.py:1299` `_report_stage`

They read deliverables, staleness and checkpoint state, and their docstrings
carry real domain reasoning — ADR-0017's two axes, and ADR-0015's rule that a
stale stage un-approves a campaign. That is core logic living in an adapter.

`app.py` is the driving adapter; this is not HTTP work. It sits there by accident
of who first needed it.

The symptom: `tests/test_staleness.py:338` defines its own `_campaign_status(client)`
helper that drives a `TestClient`, because the real one cannot be called without
going over HTTP.

## Scope

A `campaign/progress.py` module taking its ports as parameters
(`DeliverableStore`, the checkpointer) and returning domain values. `app.py`
calls it and shapes the response.

The seam is the layering boundary: the module returns stage and lifecycle facts,
never HTTP shapes. Response construction stays in `app.py`.

Best sequenced after [02](02-postgres-only-in-production.md), which makes stores
explicit parameters everywhere — `progress.py` taking them is then consistent
with the rest rather than a new idiom.

## Acceptance criteria

- [x] The four functions live in `campaign/progress.py` and take their stores as parameters.
- [x] `app.py` calls the module and only shapes responses; it holds no lifecycle derivation.
- [x] `stale_stages` is called from one place, not the four sites at `app.py:893, 1174, 1216, 1240`.
- [x] `test_staleness.py` drops its private `_campaign_status(client)` helper and calls the module directly.
- [x] The `/campaigns/{slug}/stages` response is byte-identical to before for the same state.
- [x] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.
- [x] `make test-e2e` passes.

## Comments

**2026-09-06.** Review candidate **01**, its top recommendation. Note the
justification changed in the `/grill-with-docs` session: the review argued "three
callers cross one seam" (`app.py`, `cli.py`, tests), but the CLI is removed in
[01](01-remove-the-campaign-driving-cli.md), leaving one caller and its tests.

It still earns the move on layering grounds — domain logic in an adapter — and on
the test writing its own copy to reach it. Framed as naming a missing core module,
not as deduplication.

## Completion

- Completed: 2026-09-07
- Commit: `7da05ad` — Campaign progress and the markdown field format become core modules

`campaign/progress.py` owns the derivation and returns domain values —
`CampaignProgress`, `StageProgress`, `DeliverableProgress` and plain status
strings. It imports nothing from `entrypoints/` and builds no dicts. `app.py`
keeps a `_render_stage` that turns a `StageProgress` into the contract's stage
object, and `_blocked_reason` / `_stage_progress`, which phrase things in the
operator's language for the stepper — presentation, which is the correct side of
the seam.

The `/campaigns/{slug}/stages` response is unchanged: the same six keys in the
same order with the same values, guarded by `test_workspace_contract.py`, which
asserts the field set on every stage.

**Departure from the stated scope.** `_stage_awaiting_approval` stayed in
`app.py` rather than moving with the other three. It reads the run registry and
the checkpointer — a different concern from reading deliverables — so
`campaign_progress` takes it as a callable instead. The module then depends on
the `DeliverableStore` port alone, which reads as the cleaner seam than dragging
the registry and checkpointer into it.

`stale_stages` now has exactly one caller: `stale_keys` in `progress.py`. The
four sites in `app.py` are gone.

Code review (`/code-review`, both axes) caught a real regression I introduced.
The first cut of `test_staleness.py`'s rewritten `_campaign_status` helper
stubbed `waiting=None` and `human_gate_stages=None`, which hollowed out
`test_a_campaign_with_stale_work_is_not_approved`: asserting `!= "approved"`
against a stubbed `waiting` could not distinguish "not approved because stale"
from "not approved because waiting". The helper now takes `waiting` as a
required keyword each caller names, and the test asserts `== "running"` — it
fails if the staleness clause is removed from `campaign_status`, verified by
mutation.

Also from that review: the new module shipped with no tests of its own, despite
being made testable precisely so it could have them.
`tests/test_campaign_progress.py` now drives all of it directly — both axes, the
gate-beats-staleness precedence, and the ADR-0015 rule that stale work
un-approves a finished campaign. `is_stale` was a one-line pass-through with one
caller and is gone; `stale_keys` replaced it and serves the module's own three
sites too.

**Note for [05](05-one-markdown-field-format.md).** This adds a
`campaign/ → governance/` import edge, which 05's criterion forbids. Kept
deliberately: `governance/pipeline` is already imported by seven modules across
five packages (`config.py`, `graph/`, `adapters/`, `agents/`, `billing.py`), so
it behaves as shared vocabulary rather than a package others sit below, and
progress cannot derive stage state without `PIPELINE` and `stale_stages`. 05's
criterion is about the markdown format module, which sits at the root and adds
no such edge.

Verified against a running stack: `make test-e2e` passes 43/43.
