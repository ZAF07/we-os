# 0004 — Provider-agnostic LLM access, DeepSeek as the default

The harness is designed to be **provider-agnostic**: model access goes through a single adapter (`adapters/models.py`) and, for Anthropic/OpenAI, LangChain's universal `init_chat_model` factory, with the active provider chosen by `MARKETING_OS_PROVIDER`. DeepSeek is the *default* (a cost-driven choice for development), not a strategic lock-in — Anthropic and OpenAI are first-class optional swaps (`agent-harness/pyproject.toml` extras). The priority is portability across providers, not any one vendor.

A provider-specific wrinkle is recorded here because it is surprising: **the QA reviewer runs with thinking mode disabled**. DeepSeek V4 thinking mode rejects the structured (JSON-schema) output the reviewer requires, so `reviewer_thinking` defaults to `False` (`config.py`) and `adapters/models.py` injects `extra_body={"thinking": {"type": "disabled"}}` when thinking is off. This was the fix in commit `863f255` ("fixed review agent failing due to forced structured_output").

## Consequences

- Switching providers is an env-var change plus the matching extra; no core code changes.
- The default model IDs (`deepseek-v4-pro` specialist, `deepseek-v4-flash` reviewer) still need per-account confirmation — see `.scratch/backfill/issues/02-confirm-deepseek-provider-connection.md`.
- The thinking-mode carve-out is DeepSeek-specific; other providers ignore it.

## Evidence

- `agent-harness/src/marketing_os/config.py` (`_PROVIDER_DEFAULTS`, `provider` default `deepseek`, `reviewer_thinking`).
- `adapters/models.py` (`_build_deepseek`, `extra_body` thinking disable); commit `863f255`.
- `pyproject.toml` (`langchain-deepseek` core; `anthropic`/`openai` extras).
