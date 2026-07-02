"""Agent middleware — cross-cutting hooks applied to every specialist.

The tool-error recovery middleware turns a :class:`ToolError` raised inside a
filesystem tool into a recoverable error tool-result, so the specialist reads the
failure and corrects itself rather than the exception propagating out of the tool
node and crashing the whole run. This restores the behaviour the tool docstrings
promise: ``create_agent``'s default tool node re-raises everything except
LangGraph's own argument-validation error, so a routine bad-path tool call would
otherwise be fatal.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import ToolCallRequest, wrap_tool_call
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from marketing_os.errors import ToolError


@wrap_tool_call
def recover_tool_errors(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
) -> ToolMessage | Command[Any]:
    """Convert a raised ``ToolError`` into a recoverable error tool-result.

    Args:
        request: The tool call about to run.
        handler: The callback that executes the tool.

    Returns:
        The tool's normal result, or an error ``ToolMessage`` when the tool raised
        a ``ToolError`` (for example a non-existent or mis-typed path) so the
        specialist can see the failure and retry instead of the run crashing.
    """
    try:
        return handler(request)
    except ToolError as exc:
        return ToolMessage(
            content=f"Tool error: {exc}",
            tool_call_id=request.tool_call["id"],
            status="error",
        )
