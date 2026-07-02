# Review and commit the conversation-reset refactor

Status: ready-for-human

There is staged, uncommitted work in `graph/nodes.py` and `tests/test_graph.py` that changes each specialist attempt to start from a **fresh conversation** (fresh DNA + full task context) instead of appending corrections to an accumulating transcript. The motivation is that DeepSeek V4 thinking mode rejects multi-turn histories. It needs review and a commit decision.

## What's needed

- Review the new helpers in `graph/nodes.py` (`_compose_seed()`, `_fresh_conversation()`, `_stage_task()`) and the change to `_handle_missing_deliverable()` (now takes `settings` to rebuild the full task on save-retry).
- Confirm the new test `test_revise_resets_conversation_no_transcript_accumulation()` covers the intended behaviour.
- Run `uv run ruff check .`, `uv run mypy src`, `uv run pytest`; commit if green (per CLAUDE.md, commits are on request only).

## Evidence

- `git status`: modified `agent-harness/src/marketing_os/graph/nodes.py`, `agent-harness/tests/test_graph.py`.
- Relates to commit `863f255` (the DeepSeek structured-output fix) and ADR-0004.
