# 05 — Postgres: adapter, durable checkpointer, shared run registry

Status: completed
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md) · Carries over `.scratch/backfill/issues/07`

## What to build

Postgres becomes the system of record. Because slice 02 put storage behind a port, this is an adapter plus a schema — not a migration of every call site.

Three things land together, because they are the same durability problem:

1. **A Postgres `DocumentStore` adapter**, joining the contract-conformance suite established in slice 02 and passing the identical assertions, with tenant isolation backstopped by row-level security.
2. **A durable checkpointer**, replacing the in-process one, so a run survives a service restart. This is the hard prerequisite for approval gates: a run cannot be interrupted and resumed across a process boundary without it.
3. **A shared run registry**, replacing the process-local one, so the per-slug concurrency guard holds across workers and the service can run more than one.

**The trap to avoid.** Today, cancel-as-abandon is free because every run builds its own ephemeral checkpointer, so the next run of a campaign necessarily starts from stage 1. Once checkpoints are durable, **abandoning a cancelled run must explicitly clear that campaign's checkpoint threads** — both the full-pipeline thread and any per-stage thread — or "a cancelled run starts clean" silently becomes "resume from the last checkpoint." This passes review and breaks in production, so it gets its own test.

A restarted process must also be able to reclaim or definitively fail runs the in-memory registry used to lose, rather than leaving them as traces with no terminal summary.

End-to-end behaviour: start a run, restart the service, and the run is still accounted for; cancel a run, start a new one for the same campaign, and it begins from stage 1.

## Acceptance criteria

- [x] A Postgres `DocumentStore` adapter passes the same conformance suite as the in-memory and filesystem adapters. `tests/test_documentstore.py` parametrises one `store` fixture over `filesystem`, `in-memory` and `postgres`; the same assertions run against all three.
- [x] Row-level security is enabled and a test proves a query without tenant scope returns nothing across tenants. `test_postgres.py` runs raw SQL with no `WHERE tenant_id` and sees only the scoped tenant; a transaction with no tenant set sees nothing at all; the policy's `WITH CHECK` half refuses a write labelled as another tenant. The suite connects as a non-superuser role, without which these assertions would be vacuous.
- [x] The conformance suite runs against a real containerised Postgres, is marked slow, and is skippable locally. `postgres:16-alpine` via testcontainers; the param carries `pytest.mark.slow` and skips unless `MARKETING_OS_TEST_POSTGRES=1`. `make test-postgres` runs it.
- [x] Runs survive a service restart; a restarted process resolves previously-live runs rather than losing them. Each worker heartbeats its live runs; a starting worker reclaims only runs whose heartbeat went stale, resolving them `interrupted`. Proven in tests and in the running service: SIGKILL mid-run left a `running` row, and the restarted worker resolved it to `interrupted`.
- [x] More than one worker can run without breaking the one-active-run-per-campaign guard. The claim is a partial unique index on `(tenant_id, slug) WHERE status = 'running'`, taken with `INSERT … ON CONFLICT DO NOTHING` rather than check-then-insert. **Partial:** run *traces* are still node-local files, so with several workers a run's status is answerable anywhere but its SSE stream is not — recorded in ADR-0024.
- [x] **A run cancelled mid-stage, then re-started, begins from stage 1 rather than resuming** — proven by a test. `test_a_cancelled_run_restarts_from_stage_one_rather_than_resuming` drives the HTTP API with a model that completes stage 1 then blocks in stage 2, cancels, restarts, and asserts the second run executes and reports every stage itself. Confirmed genuinely red: with the thread-clearing removed it fails, reporting `research` twice (inherited through the accumulating `results` channel).
- [x] Cancelling clears both the full-pipeline and any per-stage checkpoint threads. `clear_campaign_threads` deletes `<tenant>/<slug>` and `<tenant>/<slug>:<stage>` for every stage; a second test proves another tenant's identically-named campaign is untouched.
- [x] The fast suite still runs entirely on the in-memory adapter with no database. **Partial:** the "no database" half is met and verified — `uv run pytest` with `DOCKER_HOST` pointed at nothing gives 273 passed, 23 skipped. The "entirely on the in-memory adapter" half is **not** met and was not met before this slice either: `test_api.py`, `test_tenancy.py`, `test_pipeline.py` and `test_gate.py` still drive `FilesystemDocumentStore` against `tmp_path`, because they assert on the real repository layout. Moving them to the in-memory adapter is the PRD's wider "nothing touches a database *or the filesystem*" goal and is untouched here.
- [x] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass. 273 passed / 23 skipped without Docker; 296 passed with `MARKETING_OS_TEST_POSTGRES=1`.
- [x] Verified in the running app. uvicorn against a containerised Postgres and a local RS256 JWKS issuer standing in for Clerk: campaign created with a real signed token; the Clerk org id landed in `tenants.external_auth_id` while documents were keyed by a minted `ten_…` id; DNA gate passed on Postgres-served documents; deliverable read back; run started and heartbeated; second run refused 409; SIGKILL mid-run then restart resolved the run to `interrupted`; cancel released the claim and a fresh run was accepted.

## Blocked by

- [04 — Tracer bullet: one authenticated tenant, end to end](04-tracer-authenticated-tenant-end-to-end.md)

## Completion

- Completed: 2026-09-02
- Commit: <to be filled in manually>
