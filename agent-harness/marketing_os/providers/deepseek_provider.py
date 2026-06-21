"""DeepSeek adapter — the PRIMARY provider.

DeepSeek exposes an OpenAI-compatible `/chat/completions` API, so this adapter
is a thin specialization of `ChatCompletionsProvider`. The model id, base URL,
and API key all come from config (`DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL`,
`DEEPSEEK_API_KEY`) — nothing about the endpoint is hard-coded here.

CONFIRM before live use: the exact `deepseek-v4-pro` model id and base URL in
config.py match your DeepSeek account, and that the account's chat-completions
tool-calling matches the OpenAI shape (it does as of writing). If DeepSeek
diverges from the OpenAI tool-call contract, override the translation methods
here rather than touching the shared base.
"""

from __future__ import annotations

from ._chat_base import ChatCompletionsProvider


class DeepSeekProvider(ChatCompletionsProvider):
    name = "deepseek"
