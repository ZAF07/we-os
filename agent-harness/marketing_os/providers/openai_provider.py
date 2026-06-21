"""OpenAI adapter — a SECONDARY provider.

Thin specialization of `ChatCompletionsProvider`. Set `OPENAI_MODEL` (no default
is guessed) and optionally `OPENAI_BASE_URL` / `OPENAI_API_KEY`.
"""

from __future__ import annotations

from ._chat_base import ChatCompletionsProvider


class OpenAIProvider(ChatCompletionsProvider):
    name = "openai"
