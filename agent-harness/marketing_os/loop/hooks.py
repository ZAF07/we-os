"""Loop hooks — the cross-cutting extension points.

`LoopHooks` is the seam for behavior that wraps the loop without changing its
body: streaming output, progress logging, token-budget caps, human-in-the-loop
tool approval, tracing/metrics. `NoopHooks` is the default (does nothing).

To customize, subclass `NoopHooks` and override only the hooks you care about,
then pass an instance to your `AgentLoop`. This is a primary "fill-in" surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..types import CompletionResult, ToolCall, ToolResult

if TYPE_CHECKING:  # avoid import cycle; base imports hooks
    from .base import LoopContext, LoopResult


@runtime_checkable
class LoopHooks(Protocol):
    """Observed events over one loop run. All methods are optional to override."""

    def on_text(self, delta: str) -> None: ...

    def before_step(self, ctx: "LoopContext") -> None: ...

    def on_assistant_message(self, ctx: "LoopContext", result: CompletionResult) -> None: ...

    def before_tool_call(self, ctx: "LoopContext", call: ToolCall) -> None: ...

    def after_tool_call(self, ctx: "LoopContext", call: ToolCall, result: ToolResult) -> None: ...

    def on_finish(self, ctx: "LoopContext", result: "LoopResult") -> None: ...


class NoopHooks:
    """Default hooks: every method is a no-op. Subclass and override selectively.

    Example — a human approval gate on tool calls:

        class ApproveDestructive(NoopHooks):
            def before_tool_call(self, ctx, call):
                if call.name == "write_file":
                    # TODO: block on a real approval channel (queue, websocket, CLI prompt)
                    ...
    """

    def on_text(self, delta: str) -> None:  # noqa: D401
        return None

    def before_step(self, ctx: "LoopContext") -> None:
        return None

    def on_assistant_message(self, ctx: "LoopContext", result: CompletionResult) -> None:
        return None

    def before_tool_call(self, ctx: "LoopContext", call: ToolCall) -> None:
        return None

    def after_tool_call(self, ctx: "LoopContext", call: ToolCall, result: ToolResult) -> None:
        return None

    def on_finish(self, ctx: "LoopContext", result: "LoopResult") -> None:
        return None


class StreamToStdout(NoopHooks):
    """Convenience hooks: stream text deltas to stdout (handy for the CLI)."""

    def on_text(self, delta: str) -> None:
        import sys

        sys.stdout.write(delta)
        sys.stdout.flush()
