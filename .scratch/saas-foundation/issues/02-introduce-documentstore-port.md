# 02 — Introduce the DocumentStore port

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md) · [ADR-0001](../../../docs/adr/0001-ports-and-adapters-architecture.md)

## What to build

A behaviour-preserving prefactor. Every read and write of tenant data — Brand DNA, campaign goal, deliverables — goes through a new `DocumentStore` port instead of resolving repository paths directly. **Markdown stays the agent I/O format**; only *where a document lives* becomes pluggable. Nothing a user can observe changes.

Two adapters ship here: a filesystem adapter reproducing today's layout exactly, and an in-memory adapter that becomes the default backing for the fast test suite. A contract-conformance suite is established that runs the same assertions against every adapter — this slice sets up that harness with two adapters, and the Postgres adapter joins it later.

The port takes a tenant as an explicit argument from the outset, even though there is only one tenant until slice 04. Retrofitting the tenant argument later would touch every call site again.

End-to-end behaviour: a full campaign run behaves identically to today, but with the filesystem adapter injected; swapping in the in-memory adapter runs the same campaign with nothing written to disk.

This is the "make the change easy" step — after it, Postgres is an adapter, not a migration.

## Acceptance criteria

- [ ] A `DocumentStore` port exists with read, write, list and exists operations, each scoped by an explicit tenant argument.
- [ ] Filesystem and in-memory adapters both implement it.
- [ ] The specialists' write tool, the DNA Gate, and the stage nodes resolve documents through the port rather than composing paths themselves.
- [ ] The existing write-scope guarantee is preserved: a specialist's writes stay confined to its own campaign, and an off-slug write is still rejected.
- [ ] A contract-conformance suite runs identical assertions against both adapters and passes.
- [ ] The whole existing suite passes unchanged — this slice is observable-behaviour-neutral.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.

## Blocked by

None - can start immediately.
