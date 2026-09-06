# 02 — Postgres is the only production backend; no implicit filesystem or in-memory adapters

Status: completed
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

**4. The revision-cap rule moves above the port.**

`HUMAN_FEEDBACK`, `REVIEWER_FEEDBACK` (`adapters/deliverables.py:28,29`) and
`human_revisions_used` (`:389`) encode a domain rule — the revision cap counts
human refusals, not reviewer ones — but live in a concrete adapter. Two modules
import them from there, reaching past the `DeliverableStore` port:
`graph/nodes.py:42-44` (used at 709, 711, 763) and
`entrypoints/api/app.py:55` (used at 1881).

They are absent from `ports.py` and `schemas.py`, so any new `DeliverableStore`
must still agree with constants the filesystem adapter owns.

Move all three beside `DeliverableVersion` in `schemas.py` and update the two
imports. A pure move — no behaviour change. Folded in here because it is the
same concern as the rest of this issue: nothing above the port should depend on
a concrete adapter.

## Acceptance criteria

- [x] Starting the API with no `MARKETING_OS_POSTGRES_DSN` fails with a `ConfigError` naming the variable, rather than booting on the filesystem.
- [x] `get_backend()` has no `None` return; the three getters have no filesystem or `MemorySaver` branch.
- [x] No production code path constructs `FilesystemDocumentStore`, `FilesystemDeliverableStore` or `MemorySaver`.
- [x] The four runner parameters have no defaults; `graph.py` has no `or Filesystem…()` fallback.
- [x] API tests pass with adapters injected explicitly (see Completion — the providers are not FastAPI dependencies, so the seam is a backend override).
- [x] `HUMAN_FEEDBACK`, `REVIEWER_FEEDBACK` and `human_revisions_used` live in `schemas.py`; nothing imports them from `adapters/deliverables.py`.
- [x] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.
- [x] `make dev` comes up and a campaign runs end to end through the UI.
- [x] `make test-e2e` passes.

## Comments

**2026-09-06.** From the `/grill-with-docs` session on the architecture review.
This is review candidate **02**, deliberately scoped down: the review proposed a
frozen `Dependencies` bundle passed as one parameter. With the CLI gone there is
one entrypoint and one caller of `arun_campaign`, so bundling four parameters
into an object buys nothing. The defect worth fixing is the silent fallback, not
the parameter count.

Review candidate **04** (the revision-cap constants) is folded in as piece 4.
It carries no decision of its own — a pure import move — and belongs with this
issue's concern of keeping concrete adapters out of the layers above the port.

The 41 monkeypatch sites and 34 `cache_clear()` calls the review cites are left
alone. They are test hygiene, not a production defect, and piece 2 above reduces
the need for them where it touches.

## Completion

- Completed: 2026-09-07
- Commit: `<pending>`

Verified against a running stack, not just green tests: `make dev` brought the
stack up healthy with the DSN now mandatory, and `make test-e2e` passed 43/43 —
including the two Workspace specs that drive a campaign run through the UI, and
the `onboarding.spec.ts` case that flaked once during issue 01 (it passed here
both in the full suite and in isolation, confirming that flake as pre-existing
and unrelated).

**Deviation from piece 2, approved mid-implementation.** The issue asked for
FastAPI dependency overrides. The providers in `app.py` are not FastAPI
dependencies — they are `lru_cache` functions called directly at 54 sites,
including from background run tasks and `get_registry()`, which execute outside
any request and which `dependency_overrides` never sees. The user chose the
alternative rather than converting every endpoint.

The first cut of that alternative seeded the eight providers individually
through a module-global `_SEEDED` dict. Code review (`/code-review`, both axes)
independently flagged the same defect from two directions: Standards called it
"the mutable module global the pre-change docstring bragged about avoiding", and
Spec found the sharper consequence — `backend = None if _SEEDED else
get_backend()` put a production-reachable branch in the boot path that switched
off the very DSN gate this issue exists to add.

Rewritten as a single seam: a `StorageBackend` port in `ports.py` that both the
real `PostgresBackend` and the tests' `PrototypeBackend` satisfy, and one
`use_backend()` override. `get_backend()` is now the only seeded point, the
eight getters lost their branches and their `cast()` calls entirely, and the
lifespan opens and closes whichever backend it got — no test-shaped branch in
production startup. Storage stays one durability decision (ADR-0014): a test
swaps the whole backend, so no half-Postgres state is reachable.

Also from the review: the headline behaviour was untested. `make dev` proved it
by hand, but nothing would have caught a regression —
`test_starting_with_no_database_configured_fails_naming_the_variable`
(`tests/test_api.py`) now does.

Two smaller items folded in beyond the stated scope, both the same defect class
the issue exists to remove: `build_tools` took `document_store` as required
(it was the last implicit `FilesystemDocumentStore` construction in `src/`), and
the stale CLI references in `config.py` and a `test_quota.py` docstring were
corrected, the CLI having been removed in [01](01-remove-the-campaign-driving-cli.md).

Left as the issue directed: `graph.py`'s `checkpointer or MemorySaver()` stays —
the issue's own table makes `None` legal there, meaning "in-memory,
non-resumable", so the fallback has to live somewhere. `RunRegistry`'s
`store or InMemoryRunStore()` is untouched: the same defect class, but not in
this issue's scope and its one caller always passes a store.
