# 04 — Lift campaign progress out of the HTTP adapter

Status: ready-for-agent
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

- [ ] The four functions live in `campaign/progress.py` and take their stores as parameters.
- [ ] `app.py` calls the module and only shapes responses; it holds no lifecycle derivation.
- [ ] `stale_stages` is called from one place, not the four sites at `app.py:893, 1174, 1216, 1240`.
- [ ] `test_staleness.py` drops its private `_campaign_status(client)` helper and calls the module directly.
- [ ] The `/campaigns/{slug}/stages` response is byte-identical to before for the same state.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.
- [ ] `make test-e2e` passes.

## Comments

**2026-09-06.** Review candidate **01**, its top recommendation. Note the
justification changed in the `/grill-with-docs` session: the review argued "three
callers cross one seam" (`app.py`, `cli.py`, tests), but the CLI is removed in
[01](01-remove-the-campaign-driving-cli.md), leaving one caller and its tests.

It still earns the move on layering grounds — domain logic in an adapter — and on
the test writing its own copy to reach it. Framed as naming a missing core module,
not as deduplication.
