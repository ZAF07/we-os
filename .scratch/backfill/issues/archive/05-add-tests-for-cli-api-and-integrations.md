# Add tests for CLI, HTTP API, and integrations

Status: ready-for-agent

The graph, gate, pipeline, reviewer, loader, models, and observability layers are covered by hermetic tests (scripted model + fake reviewer, no network). Several surfaces are not covered at all.

## What's needed — untested surfaces

- `entrypoints/cli.py` — command invocation (`new-campaign`, `check`, `agents`) and error rendering.
- `entrypoints/api/app.py` — FastAPI endpoints (gate, run, stream/SSE, deliverables, runs).
- Postgres checkpointer path (only `MemorySaver` is exercised implicitly).
- Live provider integrations (no keys in CI — likely stays a manual smoke test, not automated).

## Evidence

- `agent-harness/tests/` (present: `test_graph`, `test_gate`, `test_pipeline`, `test_review`, `test_loader`, `test_models`, `test_observability`; absent: CLI, API, persistence).

## Completion

- Completed: 2026-07-02
- Commit: `f4eb0c39f6446eef1c5dfb5697b7125b4da69af2`
