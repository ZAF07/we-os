# Planned extensions: approval node, Postgres persistence, knowledge write-back

Status: needs-triage

Three capabilities are documented as intended future work but not built. Grouped here as a backlog item to triage individually when prioritised.

## Candidates

- **Human approval node** — a sign-off step before `advance` in the graph, so a person can gate a stage. The router in `graph/nodes.py` is the extension point.
- **Postgres persistence** — swap the default in-memory `MemorySaver` for `PostgresSaver` (the `postgres` extra is already declared) so runs survive process restarts.
- **Knowledge write-back** — let agents write reusable frameworks back into `knowledge/`. Deliberately inactive; activating it needs a permission grant in `.claude/settings.json` plus agent instructions (`knowledge/README.md` "Future capability").

## Open questions

- The retired Google ADK version on `origin/adk-framework-base` is superseded (ADR-0002) — can that branch be archived/deleted, or should it stay as historical reference?

## Evidence

- `agent-harness/TODO.md` (extension points: reviewer model, approval policy, persistence).
- `agent-harness/pyproject.toml` (`postgres` extra); `knowledge/README.md` (Future capability).
