"""DefaultToolUseLoop: tool dispatch round-trip + refusal handling."""

from __future__ import annotations

import pytest

from marketing_os.errors import GuardrailError
from marketing_os.loop import DefaultToolUseLoop, LoopContext
from marketing_os.tools import Tool, ToolRegistry
from marketing_os.types import Message

from conftest import FakeProvider


def _echo_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            Tool(
                name="echo",
                description="echo the input",
                parameters={"type": "object", "properties": {"text": {"type": "string"}}},
                fn=lambda text: f"echoed:{text}",
            )
        ]
    )


def test_loop_dispatches_tool_then_finishes():
    provider = FakeProvider(
        [
            {"tools": [("echo", {"text": "hi"})]},  # step 1: ask for the tool
            {"text": "done"},  # step 2: finish
        ]
    )
    ctx = LoopContext(
        provider=provider,
        system=None,
        history=[Message.user("please echo hi")],
        tools=_echo_registry(),
        max_steps=5,
        stream=False,
    )
    result = DefaultToolUseLoop().run(ctx)

    assert result.final_text == "done"
    assert result.steps == 2
    # History: user, assistant(tool_use), tool result, assistant(done)
    roles = [m.role for m in result.history]
    assert roles == ["user", "assistant", "tool", "assistant"]
    tool_msg = result.history[2]
    assert tool_msg.content == "echoed:hi"
    assert tool_msg.is_error is False


def test_loop_raises_on_refusal():
    provider = FakeProvider([{"text": "", "stop_reason": "refusal"}])
    ctx = LoopContext(
        provider=provider,
        system=None,
        history=[Message.user("do something disallowed")],
        tools=_echo_registry(),
        stream=False,
    )
    with pytest.raises(GuardrailError):
        DefaultToolUseLoop().run(ctx)


def test_loop_stops_at_max_steps():
    # Always asks for a tool -> should stop at max_steps, not loop forever.
    provider = FakeProvider([{"tools": [("echo", {"text": "x"})]} for _ in range(10)])
    ctx = LoopContext(
        provider=provider,
        system=None,
        history=[Message.user("loop")],
        tools=_echo_registry(),
        max_steps=3,
        stream=False,
    )
    result = DefaultToolUseLoop().run(ctx)
    assert result.steps == 3
