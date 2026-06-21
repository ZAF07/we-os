"""Agent loop framework: extensible scaffold + a working default."""

from __future__ import annotations

from .base import AgentLoop, LoopContext, LoopResult, ToolDispatcher
from .default import DefaultToolUseLoop
from .hooks import LoopHooks, NoopHooks, StreamToStdout

__all__ = [
    "AgentLoop",
    "LoopContext",
    "LoopResult",
    "ToolDispatcher",
    "DefaultToolUseLoop",
    "LoopHooks",
    "NoopHooks",
    "StreamToStdout",
]
