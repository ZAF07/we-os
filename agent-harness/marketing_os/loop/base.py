"""Agent loop scaffold — the framework you extend.

`AgentLoop` is the abstract base. The harness ships one working implementation
(`DefaultToolUseLoop` in `default.py`) so the pipeline runs today, but the design
intent is that you subclass `AgentLoop` (or override the marked seams) to build
your own loop behavior: custom stop conditions, budget control, planning steps,
self-reflection, parallel tool execution, etc.

Seams marked `# SEAM (fill in)` are the intended override points.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from ..providers.base import Provider
from ..types import CompletionResult, Message, ToolCall, ToolResult, Usage
from .hooks import LoopHooks, NoopHooks


@runtime_checkable
class ToolDispatcher(Protocol):
    """What the loop needs from a tool registry: schemas to advertise, and dispatch."""

    def schemas(self) -> list[dict]: ...

    def dispatch(self, call: ToolCall) -> ToolResult: ...


@dataclass
class LoopContext:
    """Mutable state threaded through a single loop run."""

    provider: Provider
    system: Optional[str]
    history: list[Message]
    tools: Optional[ToolDispatcher] = None
    max_steps: int = 20
    max_tokens: int = 16000
    stream: bool = True
    usage: Usage = field(default_factory=Usage)
    step: int = 0
    last_stop_reason: str = ""


@dataclass
class LoopResult:
    """The outcome of a loop run."""

    final_text: str
    history: list[Message]
    usage: Usage
    steps: int
    stop_reason: str


class AgentLoop(ABC):
    """Abstract agent loop. Subclass and implement `run()`, reusing the seams below."""

    def __init__(self, hooks: Optional[LoopHooks] = None) -> None:
        self.hooks: LoopHooks = hooks or NoopHooks()

    @abstractmethod
    def run(self, ctx: LoopContext) -> LoopResult:
        """Drive the conversation to completion and return the result."""
        raise NotImplementedError

    # ── Seams (override to customize; defaults are sensible) ──────────────────

    def prepare_messages(self, ctx: LoopContext) -> list[Message]:
        """Messages to send this step. Default: the full history.

        # SEAM (fill in): inject reminders, trim/compact context, add scratchpad.
        """
        return ctx.history

    def model_turn(self, ctx: LoopContext) -> CompletionResult:
        """One provider call. Centralized so subclasses can wrap/log/retry it."""
        result = ctx.provider.complete(
            system=ctx.system,
            messages=self.prepare_messages(ctx),
            tools=ctx.tools.schemas() if ctx.tools else None,
            max_tokens=ctx.max_tokens,
            stream=ctx.stream,
            on_text=self.hooks.on_text,
        )
        ctx.usage = ctx.usage + result.usage
        ctx.last_stop_reason = result.stop_reason
        return result

    def execute_tool(self, ctx: LoopContext, call: ToolCall) -> ToolResult:
        """Dispatch a single tool call through the registry.

        # SEAM (fill in): approval gates, sandboxing, parallelism, mocking.
        """
        self.hooks.before_tool_call(ctx, call)
        if ctx.tools is None:
            result = ToolResult(tool_call_id=call.id, content="No tools available.", is_error=True)
        else:
            result = ctx.tools.dispatch(call)
        self.hooks.after_tool_call(ctx, call, result)
        return result

    def should_continue(self, ctx: LoopContext, result: CompletionResult) -> bool:
        """Whether to take another step. Default: continue iff the model asked for tools.

        # SEAM (fill in): budget caps, max-tool-call limits, custom stop signals.
        """
        if ctx.step >= ctx.max_steps:
            return False
        return result.stop_reason == "tool_use" and bool(result.tool_calls)

    def on_finish(self, ctx: LoopContext, result: LoopResult) -> None:
        """Called once the loop ends. Default: notify hooks.

        # SEAM (fill in): persistence, metrics flush, summary generation.
        """
        self.hooks.on_finish(ctx, result)
