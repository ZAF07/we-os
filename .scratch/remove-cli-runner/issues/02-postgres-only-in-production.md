# 02 — Postgres is the only production backend; no implicit filesystem or in-memory adapters

Status: ready-for-agent
Type: task

## Parent

[ADR-0026](../../../docs/adr/0026-the-api-is-the-only-campaign-execution-surface.md) · blocked by [01](01-remove-the-campaign-driving-cli.md)

## Why

`get_backend()` returns `None` when `MARKETING_OS_POSTGRES_DSN` is unset, and
every provider below it falls through to a prototype adapter — filesystem stores
and a `MemorySaver`. A production deploy with a missing or mistyped DSN boots
healthy, writes campaigns to local disk, and runs with a checkpointer that does
not survive a restart. Nothing warns.

The filesystem stores and `MemorySaver` were prototype scaffolding. They stay in
the tree — they are useful for tests — but nothing may select them implicitly.

## Scope

**1. The DSN becomes mandatory.**

`get_backend()` returns `PostgresBackend`, never `None`, and raises `ConfigError`
with a clear message when no DSN is configured. Its docstring already calls it
"the single place the storage choice is made"; it becomes the single place the
choice is enforced. `get_document_store`, `get_deliverable_store` and
`get_checkpointer` lose their fallback branches.

Both compose stacks already set the DSN
(`docker-compose.yml:83`, `docker-compose.e2e.yml:70`), so `make dev` and
`make test-e2e` are unaffected.

**2. API tests inject their adapters explicitly.**

The ~10 files building a `TestClient` against a hermetic repo currently inherit
the filesystem fallback. They get a shared helper — beside `authenticate()` and
`install_scripted_graph()` in the test support module, not in `app.py` — that
overrides the four providers with filesystem/memory adapters through FastAPI
dependency overrides.

Tests that want prototype adapters say so. That is the whole point: no code path
selects them implicitly, in production or in tests.

**3. The runner's adapters become required.**

`arun_campaign` and `build_campaign_graph` / the single-stage builder take these
as required keyword parameters, and the `or Default(...)` fallbacks in
`graph.py` go:

| Parameter | Required | `None` legal | `None` means |
| --- | --- | --- | --- |
| `document_store` | yes | no | — |
| `deliverable_store` | yes | no | — |
| `usage_ledger` | yes | yes | uncharged (ADR-0020) |
| `checkpointer` | yes | yes | in-memory, non-resumable |

No defaults, rather than no `None`. A silent fallback becomes an explicit choice,
and the two legitimate modes stay reachable by saying so. Update the docstrings
at `graph.py:199-210` and `271-281`, which currently describe the defaults and
cite the CLI as a reason for the uncharged mode.

## Acceptance criteria

- [ ] Starting the API with no `MARKETING_OS_POSTGRES_DSN` fails with a `ConfigError` naming the variable, rather than booting on the filesystem.
- [ ] `get_backend()` has no `None` return; the three getters have no filesystem or `MemorySaver` branch.
- [ ] No production code path constructs `FilesystemDocumentStore`, `FilesystemDeliverableStore` or `MemorySaver`.
- [ ] The four runner parameters have no defaults; `graph.py` has no `or Filesystem…()` fallback.
- [ ] API tests pass with adapters injected through dependency overrides.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.
- [ ] `make dev` comes up and a campaign runs end to end through the UI.
- [ ] `make test-e2e` passes.

## Comments

**2026-09-06.** From the `/grill-with-docs` session on the architecture review.
This is review candidate **02**, deliberately scoped down: the review proposed a
frozen `Dependencies` bundle passed as one parameter. With the CLI gone there is
one entrypoint and one caller of `arun_campaign`, so bundling four parameters
into an object buys nothing. The defect worth fixing is the silent fallback, not
the parameter count.

The 41 monkeypatch sites and 34 `cache_clear()` calls the review cites are left
alone. They are test hygiene, not a production defect, and piece 2 above reduces
the need for them where it touches.
