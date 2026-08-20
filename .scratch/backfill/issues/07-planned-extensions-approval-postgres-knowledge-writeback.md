# Planned extensions: approval node, Postgres persistence, knowledge write-back

Status: needs-triage

Three capabilities are documented as intended future work but not built. Grouped here as a backlog item to triage individually when prioritised.

## Candidates

- **Human approval node** — a sign-off step before `advance` in the graph, so a person can gate a stage. The router in `graph/nodes.py` is the extension point.
- **Postgres persistence** — swap the default in-memory `MemorySaver` for `PostgresSaver` (the `postgres` extra is already declared) so runs survive process restarts.
  - **Carry-over from run-lifecycle issue 02 / [ADR-0010](../../../docs/adr/0010-background-job-run-model.md):** cancel-as-abandon is currently free because every run builds its own ephemeral `MemorySaver`, so the next run of a slug re-runs from stage 1. Once a persistent checkpointer is wired, **abandon must explicitly clear the cancelled slug's checkpoint thread** (both the full-pipeline `thread_id = slug` and any `slug:stage` thread), otherwise "a cancelled run starts clean" silently becomes "resume from the last checkpoint." Add a test that a run cancelled mid-stage, then re-started, begins from stage 1 rather than resuming.
  - Persisting run state would also let a restarted process reclaim (or definitively fail) runs that the in-memory `RunRegistry` currently loses on restart — today such a run resolves to `interrupted` (trace with no terminal summary). A durable/shared registry is also the prerequisite for running more than one uvicorn worker without breaking the per-slug concurrency guard, which is currently process-local.
- **Knowledge write-back** — let agents write reusable frameworks back into `knowledge/`. Deliberately inactive; activating it needs a permission grant in `.claude/settings.json` plus agent instructions (`knowledge/README.md` "Future capability").

## Open questions

- The retired Google ADK version on `origin/adk-framework-base` is superseded (ADR-0002) — can that branch be archived/deleted, or should it stay as historical reference?

## Evidence

- `agent-harness/TODO.md` (extension points: reviewer model, approval policy, persistence).
- `agent-harness/pyproject.toml` (`postgres` extra); `knowledge/README.md` (Future capability).

## Comments

**2026-08-20 — triaged; two of three candidates decided, scope expanded.** A design session settled the product shape (multi-tenant SaaS, FE↔BE wiring, creative assets, Meta/TikTok). Outcome:

- **Human approval node — decided and expanded.** Not a single node: a per-stage approval policy with `interrupt()`/resume and `approve`/`revise` endpoints, plus immutable deliverable versions and downstream staleness. See [ADR-0015](../../../docs/adr/0015-human-approval-gates-and-versioned-deliverables.md).
- **Postgres persistence — decided and expanded well beyond the checkpointer.** Postgres becomes the system of record for all tenant data behind a `DocumentStore` port, plus the questionnaire, guardrails and knowledge library. See [ADR-0014](../../../docs/adr/0014-postgres-system-of-record-and-split-governance.md). The abandon-must-clear-the-thread carry-over recorded above still stands and is restated in that ADR.
- **Knowledge write-back — still not decided.** Untouched by this session; remains a candidate.

Note the ordering constraint this creates: Postgres is a **hard prerequisite** for the approval work (LangGraph cannot resume an interrupted run across a process boundary on `MemorySaver`), and both precede any real FE↔BE wiring.

Related new decisions: [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md) (tenancy/auth), [ADR-0016](../../../docs/adr/0016-channel-planning-precedes-creative.md) (stage reorder), [ADR-0017](../../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md) (FE↔engine mapping), [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md) (DNA authoring), [ADR-0019](../../../docs/adr/0019-creative-unit-is-the-approvable-asset.md) (assets), [ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) (quota), [ADR-0021](../../../docs/adr/0021-organic-publishing-before-paid-ads.md) (publishing).
