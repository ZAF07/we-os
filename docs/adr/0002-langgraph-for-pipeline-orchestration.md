# 0002 — LangGraph for pipeline orchestration

Status: accepted — supersedes the hand-rolled loop (`8c05f37`) and the Google ADK version (`3998d9d`, `467c321`, on `origin/adk-framework-base`).

The campaign pipeline is orchestrated as a LangGraph `StateGraph` over a `CampaignState` (`graph/state.py`): a gate node, then per-stage `enter → specialist → review` nodes with conditional routing (`revise` loops back to the specialist; `advance` moves on; `fail`/`end` halt). We adopted LangGraph for durable, checkpointable, streamable orchestration with explicit per-stage QA loops, replacing two earlier approaches that hand-coded the control flow.

Two prior designs were tried and dropped: the original had a bespoke `loop/` + `orchestrator.py` + `providers/` (`8c05f37`); the second built on Google ADK (`3998d9d`, `467c321`). The LangGraph rewrite (`d5d5ed6` "first refactor to langgraph", then `d5b1dfc`, `863f255`) deleted both and moved the code under `src/marketing_os/graph/`. The ADK branch is **retired** — kept only as historical reference on `origin/adk-framework-base`, not a maintained fallback.

## Consequences

- State, routing, checkpointing (`MemorySaver` by default; Postgres optional), and streaming come from the framework instead of custom code.
- LangGraph 1.0 + LangChain 1.0 are now core dependencies and a hard architectural commitment (`agent-harness/pyproject.toml`).
- The migration is on `migrate-to-langgraph` and not yet merged to `main`.

## Evidence

- Commits `8c05f37`, `3998d9d`, `467c321`, `d5d5ed6`, `d5b1dfc`, `863f255`.
- `graph/graph.py`, `graph/nodes.py`, `graph/state.py`, `graph/runner.py`; `pyproject.toml` (`langgraph>=1.0`).
