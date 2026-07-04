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
