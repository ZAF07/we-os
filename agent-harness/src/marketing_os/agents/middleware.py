"""Agent middleware — cross-cutting hooks applied to every specialist.

The tool-error recovery middleware turns a :class:`ToolError` raised inside a
filesystem tool into a recoverable error tool-result, so the specialist reads the
failure and corrects itself rather than the exception propagating out of the tool
node and crashing the whole run. This restores the behaviour the tool docstrings
promise: ``create_agent``'s default tool node re-raises everything except
LangGraph's own argument-validation error, so a routine bad-path tool call would
otherwise be fatal.

Both the sync and async hooks are implemented because the specialist runs on the
async graph path (ADR-0009); ``create_agent`` dispatches to ``awrap_tool_call``
when the agent is invoked with ``ainvoke``/``astream``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from marketing_os.errors import ToolError


class RecoverToolErrors(AgentMiddleware):
    """Middleware that turns a raised ``ToolError`` into a recoverable result."""

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Run a tool synchronously, recovering a raised ``ToolError``.

        Args:
            request: The tool call about to run.
            handler: The callback that executes the tool.

        Returns:
            The tool's normal result, or an error ``ToolMessage`` when the tool
            raised a ``ToolError`` so the specialist can retry instead of crashing.
        """
        try:
            return handler(request)
        except ToolError as exc:
            return _tool_error_message(request, exc)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Run a tool on the async path, recovering a raised ``ToolError``.

        Args:
            request: The tool call about to run.
            handler: The async callback that executes the tool.

        Returns:
            The tool's normal result, or an error ``ToolMessage`` when the tool
            raised a ``ToolError`` so the specialist can retry instead of crashing.
        """
        try:
            return await handler(request)
        except ToolError as exc:
            return _tool_error_message(request, exc)


def _tool_error_message(request: ToolCallRequest, exc: ToolError) -> ToolMessage:
    """Build the recoverable error tool-result for a raised ``ToolError``.

    Args:
        request: The tool call that failed.
        exc: The tool error raised by the filesystem tool.

    Returns:
        An error-status ``ToolMessage`` the specialist reads and corrects from.
    """
    return ToolMessage(
        content=f"Tool error: {exc}",
        tool_call_id=request.tool_call["id"],
        status="error",
    )


recover_tool_errors = RecoverToolErrors()
