"""Tool definitions + registry.

A `Tool` bundles a normalized schema (advertised to the model) with the Python
callable that executes it. `ToolRegistry` advertises schemas and dispatches calls,
converting any exception into an error tool-result the model can recover from —
it never lets a tool crash the loop. `build_registry()` assembles the concrete
tools an agent is granted, from the Claude-style capability names in its
frontmatter (`Read, Grep, Glob, Write, WebSearch, WebFetch`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..errors import ToolError
from ..types import ToolCall, ToolResult


@dataclass
class Tool:
    """An executable tool: schema advertised to the model + the function behind it."""

    name: str
    description: str
    parameters: dict  # JSON Schema
    fn: Callable[..., str]


class ToolRegistry:
    """Holds the tools an agent may call; advertises schemas and dispatches calls."""

    def __init__(self, tools: Optional[list[Tool]] = None) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools or []:
            self.add(t)

    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def schemas(self) -> list[dict]:
        """Normalized tool schemas for the provider layer."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._tools.values()
        ]

    def dispatch(self, call: ToolCall) -> ToolResult:
        """Execute a tool call, returning an error tool-result on any failure."""
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                tool_call_id=call.id,
                content=f"Unknown tool '{call.name}'. Available: {', '.join(self._tools)}.",
                is_error=True,
            )
        try:
            output = tool.fn(**call.arguments)
            return ToolResult(tool_call_id=call.id, content=str(output), is_error=False)
        except ToolError as exc:
            return ToolResult(tool_call_id=call.id, content=f"Error: {exc}", is_error=True)
        except TypeError as exc:
            return ToolResult(
                tool_call_id=call.id,
                content=f"Error: bad arguments for '{call.name}': {exc}",
                is_error=True,
            )
        except Exception as exc:  # noqa: BLE001 - tools must never crash the loop
            return ToolResult(tool_call_id=call.id, content=f"Error: {exc}", is_error=True)


def build_registry(
    declared_tools: list[str],
    *,
    sandbox,
    web_backend=None,
) -> ToolRegistry:
    """Map an agent's declared capabilities to concrete Tool instances.

    Args:
        declared_tools: capability names from the agent frontmatter
            (e.g. ["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch"]).
        sandbox: a FilesystemSandbox.
        web_backend: a WebSearchTool (defaults to NoopWebSearch) — only used if
            the agent declares WebSearch/WebFetch.
    """
    from .filesystem import filesystem_tools
    from .websearch import NoopWebSearch, web_tools

    declared = set(declared_tools)
    available: dict[str, Tool] = {}

    fs = filesystem_tools(sandbox, include_write="Write" in declared)
    available.update(fs)

    if declared & {"WebSearch", "WebFetch"}:
        available.update(web_tools(web_backend or NoopWebSearch()))

    selected = [tool for cap, tool in available.items() if cap in declared]
    return ToolRegistry(selected)
