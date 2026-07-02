# 0001 — Ports-and-adapters (hexagonal) architecture

The `agent-harness` isolates its domain/orchestration core from external systems (LLM providers, the QA judge, the web, the filesystem) behind explicit ports, with concrete adapters injected at graph-build time. We chose this so the pipeline can be tested end-to-end without network or API keys, and so a provider or reviewer can be swapped without touching the graph.

The one first-class port is the QA judge: `Reviewer` (a `runtime_checkable` `Protocol`) in `agent-harness/src/marketing_os/ports.py:17`. Adapters live under `agent-harness/src/marketing_os/adapters/` (`models.py`, `review.py` implementing `Reviewer`, `observability.py`, `tools/`). Dependency injection is via `build_campaign_graph(settings, *, model=, reviewer=, web_backend=, checkpointer=)` in `graph/graph.py`; tests inject `FakeReviewer` and a scripted `ProgrammableChatModel` (see `tests/conftest.py`).

## Consequences

- Behaviour is coded as CLAUDE.md's standing standard ("Follow the ports-and-adapters pattern"), so new integrations add an adapter rather than editing the core.
- Not every dependency is a formal `Protocol` yet — the chat model relies on LangChain's `BaseChatModel` and the sandbox is a concrete class; `Reviewer` is the only project-defined port.

## Evidence

- `CLAUDE.md` coding standards.
- `agent-harness/src/marketing_os/ports.py`, `adapters/review.py` (`LLMReviewer`), `adapters/models.py`, `adapters/tools/sandbox.py`.
- `graph/graph.py` (`build_campaign_graph` injection points); `tests/conftest.py`.
