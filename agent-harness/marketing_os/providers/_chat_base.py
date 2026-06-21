"""Shared implementation for OpenAI-compatible chat-completions backends.

Both the primary DeepSeek adapter and the OpenAI adapter speak this wire format,
so the translation logic lives here once. The official `openai` SDK is the
client for both — only the base URL, key, and model differ (set via config).
"""

from __future__ import annotations

import json
from typing import Optional

from ..errors import ProviderError
from ..types import CompletionResult, Message, ToolCall, Usage
from .base import OnText, Provider, ToolSchema

# Map chat-completions finish_reason -> the harness's normalized stop_reason.
_FINISH_MAP = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}


class ChatCompletionsProvider(Provider):
    """Base adapter for any OpenAI-compatible `/chat/completions` endpoint."""

    name = "chat"

    def __init__(self, config) -> None:
        super().__init__(config)
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ProviderError(
                f"The '{self.name}' adapter needs the openai SDK. "
                f"Install it: pip install 'marketing-os[openai]'."
            ) from exc
        kwargs: dict = {}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = OpenAI(**kwargs)

    # ── Translation: normalized history -> chat-completions messages ──────────
    def _to_wire(self, system: Optional[str], messages: list[Message]) -> list[dict]:
        wire: list[dict] = []
        if system:
            wire.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                wire.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id,
                        "content": m.content or "",
                    }
                )
            elif m.role == "assistant":
                if m.provider_native is not None and m.provider == self.name:
                    wire.append(m.provider_native)
                else:
                    entry: dict = {"role": "assistant", "content": m.content or ""}
                    if m.tool_calls:
                        entry["content"] = m.content or None
                        entry["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in m.tool_calls
                        ]
                    wire.append(entry)
            else:  # user (and any system messages already handled above)
                wire.append({"role": m.role, "content": m.content or ""})
        return wire

    @staticmethod
    def _tools_to_wire(tools: Optional[list[ToolSchema]]) -> Optional[list[dict]]:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    @staticmethod
    def _parse_arguments(raw: str | None) -> dict:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Surface malformed arguments rather than crashing the loop; the tool
            # layer will return an error tool-result the model can recover from.
            return {"__raw__": raw}

    # ── Completion ────────────────────────────────────────────────────────────
    def complete(
        self,
        *,
        system: Optional[str],
        messages: list[Message],
        tools: Optional[list[ToolSchema]] = None,
        max_tokens: int = 16000,
        stream: bool = True,
        on_text: Optional[OnText] = None,
    ) -> CompletionResult:
        wire_messages = self._to_wire(system, messages)
        wire_tools = self._tools_to_wire(tools)
        kwargs: dict = {
            "model": self.config.model,
            "messages": wire_messages,
            "max_tokens": max_tokens,
        }
        if wire_tools:
            kwargs["tools"] = wire_tools

        if stream:
            return self._complete_streaming(kwargs, on_text)
        return self._complete_blocking(kwargs)

    def _complete_blocking(self, kwargs: dict) -> CompletionResult:
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        text = msg.content or ""
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=self._parse_arguments(tc.function.arguments),
            )
            for tc in (msg.tool_calls or [])
        ]
        usage = self._usage(getattr(resp, "usage", None))
        return self._build_result(text, tool_calls, choice.finish_reason, usage)

    def _complete_streaming(self, kwargs: dict, on_text: Optional[OnText]) -> CompletionResult:
        kwargs = {**kwargs, "stream": True, "stream_options": {"include_usage": True}}
        text_parts: list[str] = []
        acc: dict[int, dict] = {}
        finish_reason = "stop"
        usage_obj = None
        for chunk in self._client.chat.completions.create(**kwargs):
            if getattr(chunk, "usage", None):
                usage_obj = chunk.usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if getattr(delta, "content", None):
                text_parts.append(delta.content)
                if on_text:
                    on_text(delta.content)
            for tcd in getattr(delta, "tool_calls", None) or []:
                slot = acc.setdefault(tcd.index, {"id": "", "name": "", "args": ""})
                if tcd.id:
                    slot["id"] = tcd.id
                if tcd.function and tcd.function.name:
                    slot["name"] = tcd.function.name
                if tcd.function and tcd.function.arguments:
                    slot["args"] += tcd.function.arguments
            if choice.finish_reason:
                finish_reason = choice.finish_reason
        tool_calls = [
            ToolCall(id=s["id"], name=s["name"], arguments=self._parse_arguments(s["args"]))
            for _, s in sorted(acc.items())
        ]
        return self._build_result(
            "".join(text_parts), tool_calls, finish_reason, self._usage(usage_obj)
        )

    @staticmethod
    def _usage(u) -> Usage:
        if u is None:
            return Usage()
        return Usage(
            input_tokens=getattr(u, "prompt_tokens", 0) or 0,
            output_tokens=getattr(u, "completion_tokens", 0) or 0,
        )

    def _build_result(self, text, tool_calls, finish_reason, usage) -> CompletionResult:
        stop_reason = _FINISH_MAP.get(finish_reason or "stop", "end_turn")
        if tool_calls:
            stop_reason = "tool_use"
        # Reconstruct the assistant turn for verbatim replay on the next request.
        native: dict = {"role": "assistant", "content": text or (None if tool_calls else "")}
        if tool_calls:
            native["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in tool_calls
            ]
        assistant = Message(
            role="assistant",
            content=text,
            tool_calls=tool_calls,
            provider_native=native,
            provider=self.name,
        )
        return CompletionResult(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            assistant_message=assistant,
        )
