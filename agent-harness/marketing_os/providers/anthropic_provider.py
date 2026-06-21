"""Anthropic (Claude) adapter — a SECONDARY provider.

Faithful to the Claude API guidance: model `claude-opus-4-8`, adaptive thinking,
streaming via `messages.stream()` + `get_final_message()`, and — critically —
the assistant turn is replayed back as the raw `response.content` blocks
(including thinking blocks) via `provider_native`, never reconstructed from text.
The SDK auto-retries 429/5xx.
"""

from __future__ import annotations

from typing import Optional

from ..errors import ProviderError
from ..types import CompletionResult, Message, ToolCall, Usage
from .base import OnText, Provider, ToolSchema


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, config) -> None:
        super().__init__(config)
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ProviderError(
                "The 'anthropic' adapter needs the anthropic SDK. "
                "Install it: pip install 'marketing-os[anthropic]'."
            ) from exc
        kwargs: dict = {}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = anthropic.Anthropic(**kwargs)

    # ── Translation: normalized history -> Anthropic messages ─────────────────
    def _to_wire(self, messages: list[Message]) -> list[dict]:
        wire: list[dict] = []
        pending_tool_results: list[dict] = []

        def flush() -> None:
            nonlocal pending_tool_results
            if pending_tool_results:
                wire.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []

        for m in messages:
            if m.role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id,
                    "content": m.content or "",
                }
                if m.is_error:
                    block["is_error"] = True
                pending_tool_results.append(block)
                continue
            flush()
            if m.role == "assistant":
                if m.provider_native is not None and m.provider == self.name:
                    # Replay raw content blocks verbatim (preserves thinking blocks).
                    wire.append({"role": "assistant", "content": m.provider_native})
                else:
                    blocks: list[dict] = []
                    if m.content:
                        blocks.append({"type": "text", "text": m.content})
                    for tc in m.tool_calls:
                        blocks.append(
                            {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                        )
                    wire.append({"role": "assistant", "content": blocks or ""})
            else:  # user
                wire.append({"role": "user", "content": m.content or ""})
        flush()
        return wire

    @staticmethod
    def _tools_to_wire(tools: Optional[list[ToolSchema]]) -> Optional[list[dict]]:
        if not tools:
            return None
        return [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
            }
            for t in tools
        ]

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
        kwargs: dict = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": self._to_wire(messages),
        }
        if system:
            kwargs["system"] = system
        wire_tools = self._tools_to_wire(tools)
        if wire_tools:
            kwargs["tools"] = wire_tools
        if self.config.thinking:
            kwargs["thinking"] = {"type": "adaptive"}

        if stream:
            with self._client.messages.stream(**kwargs) as s:
                for event in s:
                    if (
                        event.type == "content_block_delta"
                        and getattr(event.delta, "type", None) == "text_delta"
                    ):
                        if on_text:
                            on_text(event.delta.text)
                msg = s.get_final_message()
        else:
            msg = self._client.messages.create(**kwargs)
        return self._parse(msg)

    def _parse(self, msg) -> CompletionResult:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in msg.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
        u = msg.usage
        usage = Usage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )
        text = "".join(text_parts)
        assistant = Message(
            role="assistant",
            content=text,
            tool_calls=tool_calls,
            provider_native=msg.content,  # raw blocks, replayed verbatim
            provider=self.name,
        )
        return CompletionResult(
            text=text,
            tool_calls=tool_calls,
            stop_reason=msg.stop_reason or "end_turn",
            usage=usage,
            assistant_message=assistant,
        )
