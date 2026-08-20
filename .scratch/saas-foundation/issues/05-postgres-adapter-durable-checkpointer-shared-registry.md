# 05 — Postgres: adapter, durable checkpointer, shared run registry

Status: ready-for-agent
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

- [ ] A Postgres `DocumentStore` adapter passes the same conformance suite as the in-memory and filesystem adapters.
- [ ] Row-level security is enabled and a test proves a query without tenant scope returns nothing across tenants.
- [ ] The conformance suite runs against a real containerised Postgres, is marked slow, and is skippable locally.
- [ ] Runs survive a service restart; a restarted process resolves previously-live runs rather than losing them.
- [ ] More than one worker can run without breaking the one-active-run-per-campaign guard.
- [ ] **A run cancelled mid-stage, then re-started, begins from stage 1 rather than resuming** — proven by a test.
- [ ] Cancelling clears both the full-pipeline and any per-stage checkpoint threads.
- [ ] The fast suite still runs entirely on the in-memory adapter with no database.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app.

## Blocked by

- [04 — Tracer bullet: one authenticated tenant, end to end](04-tracer-authenticated-tenant-end-to-end.md)
