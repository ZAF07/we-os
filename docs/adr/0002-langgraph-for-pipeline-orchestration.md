# 0002 — LangGraph for pipeline orchestration

Status: accepted — supersedes the hand-rolled loop (`8c05f37`) and a Google ADK proof of concept.

The campaign pipeline is orchestrated as a LangGraph `StateGraph` over a `CampaignState` (`graph/state.py`): a gate node, then per-stage `enter → specialist → review` nodes with conditional routing (`revise` loops back to the specialist; `advance` moves on; `fail`/`end` halt). We adopted LangGraph for durable, checkpointable, streamable orchestration with explicit per-stage QA loops, replacing two earlier approaches that hand-coded the control flow.

Two prior designs were tried and dropped. The original had a bespoke `loop/` + `orchestrator.py` + `providers/` (`8c05f37`). The second was a proof of concept built on Google ADK, which placed the harness at `agent-harness/marketing_os/` without the `src/` layer and hand-coded its own agent registry, guardrail callbacks and run state. Neither gave us durable checkpointing or resumable runs without writing that machinery ourselves, which is what LangGraph provides off the shelf.

The LangGraph rewrite (`d5d5ed6` "first refactor to langgraph", then `d5b1dfc`, `863f255`) deleted both and moved the code under `src/marketing_os/graph/`. **The ADK proof of concept has been deleted outright** — its branch and its commits are gone, deliberately, so nothing invites a reader to treat it as a fallback. It is recorded here rather than in the history.

## Consequences

- State, routing, checkpointing (`MemorySaver` by default; Postgres optional), and streaming come from the framework instead of custom code.
- LangGraph 1.0 + LangChain 1.0 are now core dependencies and a hard architectural commitment (`agent-harness/pyproject.toml`).
- The migration is merged; LangGraph orchestration is what `main` runs.

## Evidence

- Commits `8c05f37`, `d5d5ed6`, `d5b1dfc`, `863f255`. The two ADK commits are deliberately not cited — they no longer exist.
- `graph/graph.py`, `graph/nodes.py`, `graph/state.py`, `graph/runner.py`; `pyproject.toml` (`langgraph>=1.0`).
