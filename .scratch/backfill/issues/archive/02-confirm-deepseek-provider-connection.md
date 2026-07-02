# Confirm the DeepSeek provider connection and model IDs

Status: completed

The default provider is DeepSeek with model IDs `deepseek-v4-pro` (specialist) and `deepseek-v4-flash` (reviewer). These defaults need per-account confirmation — the exact model ID available on the operator's DeepSeek account may differ, and no live provider call is exercised in tests.

## What's needed

- Confirm the correct model IDs for the account; set `DEEPSEEK_API_KEY`, and optionally `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL`.
- Alternatively swap providers entirely with `MARKETING_OS_PROVIDER=anthropic|openai` plus the matching extra and key (see ADR-0004 — the design is provider-agnostic).
- Do a single live smoke run to verify the connection end-to-end.

## Open questions

- Are `deepseek-v4-pro` / `deepseek-v4-flash` the intended production models, or placeholders pending account confirmation?

## Evidence

- `agent-harness/src/marketing_os/config.py` (`_PROVIDER_DEFAULTS`).
- `agent-harness/TODO.md` §1a; `docs/adr/0004-provider-agnostic-llm-with-deepseek-default.md`.

## Completion

- Completed: 2026-07-02
- Commit: N/A (human approved)
