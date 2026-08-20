# 07 — Approval gates: interrupt/resume and versioned revision

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0015](../../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md)

## What to build

The feature that makes we-OS a decision-making system rather than a generator: the run stops and asks.

Each Stage carries an **approval policy** — `auto` (advance when the QA reviewer passes it) or `human` (halt and wait for a person). Defaults: research `auto`; brand-strategy, campaign-strategy, performance-plan, creative-brief and asset-prompts `human`. The policy is **data, not code**, so tightening or loosening it later is a configuration change.

A `human`-policy stage halts at an Approval Gate. The campaign's lifecycle status becomes `awaiting_approval`. The person reads the full deliverable and either:

- **approves**, and the run resumes automatically into the next stage; or
- **revises with written feedback**, which re-runs the stage with that feedback and writes a **new version** of the deliverable carrying the feedback that prompted it. Nothing is overwritten.

Deliverables become immutable and versioned, each version recording what it supersedes and whether its prompting feedback came from a person or the QA reviewer. This machinery is deliberately built here because the creative-asset review loop reuses it wholesale.

The Approval Gate is distinct from the QA reviewer: the reviewer is a model scoring against a Guardrail, the gate is a human decision. Both can send a stage back; only the gate blocks progress on a person.

This slice is where the documented constraint finally holds: **creative cannot be produced before a human-approved strategy exists.**

End-to-end behaviour: start a run, watch it work through research automatically, stop at brand strategy; read it, send it back with feedback, get a version 2, approve that, and watch the run continue to campaign strategy.

## Acceptance criteria

- [ ] Each stage's approval policy is data and is reported by the API alongside the stage.
- [ ] A `human`-policy stage halts and the run does not advance until an explicit approval.
- [ ] The campaign's lifecycle status reads `awaiting_approval` while halted, distinct from its stage progress.
- [ ] Approving resumes the run into the next stage without a new run being started.
- [ ] Revising with feedback re-runs the stage and produces a new version; the prior version is still readable.
- [ ] Each version records the feedback that prompted it and whether it came from a person or the reviewer.
- [ ] Version history for a deliverable is retrievable in order.
- [ ] An `auto`-policy stage still advances on a passing QA verdict with no human involvement.
- [ ] A halted run survives a service restart and can still be approved afterwards.
- [ ] Asset prompts cannot be produced while any upstream `human` stage is unapproved.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy src` all pass.
- [ ] Verified in the running app.

## Blocked by

- [05 — Postgres: adapter, durable checkpointer, shared run registry](05-postgres-adapter-durable-checkpointer-shared-registry.md)
