"""LangSmith tracing configuration and per-run invocation config.

Turns on LangChain's native LangSmith tracing (the primary deep prompt/tool/
response surface) when its environment is present, mints the sortable run id that
names a run's trace, and builds the LangGraph invocation config that carries the
LangSmith run name, metadata, and tags.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from marketing_os.adapters.observability.console import get_logger
from marketing_os.config import Settings

_TRACING_ENV_VARS = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")
_DEFAULT_PROJECT = "marketing-os"


def _env_is_true(value: str | None) -> bool:
    """Return whether an environment value is a truthy flag.

    Args:
        value: The raw environment value, or ``None``.

    Returns:
        ``True`` if the value is set to a common truthy token.
    """
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def tracing_enabled() -> bool:
    """Return whether LangSmith tracing is enabled by the environment.

    Returns:
        ``True`` if either LangSmith tracing flag is set to a truthy value.
    """
    return any(_env_is_true(os.environ.get(var)) for var in _TRACING_ENV_VARS)


def configure_tracing(settings: Settings) -> bool:
    """Enable LangSmith run naming when tracing is turned on via the environment.

    LangChain performs the actual tracing when ``LANGSMITH_TRACING`` (or
    ``LANGCHAIN_TRACING_V2``) and an API key are set. This only defaults the
    project name so runs are grouped, and logs that tracing is active.

    Args:
        settings: The harness settings (used for logging context).

    Returns:
        ``True`` if tracing is enabled, ``False`` otherwise.
    """
    if not tracing_enabled():
        return False
    os.environ.setdefault("LANGCHAIN_PROJECT", _DEFAULT_PROJECT)
    get_logger().info(
        "LangSmith tracing enabled (project=%s)",
        os.environ.get("LANGCHAIN_PROJECT", _DEFAULT_PROJECT),
    )
    return True


def new_run_id() -> str:
    """Return a sortable, unique run id.

    Returns:
        A ``<UTC-timestamp>-<short-uuid>`` identifier.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid4().hex[:8]}"


def run_config(
    thread_id: str,
    *,
    run_name: str,
    metadata: dict[str, Any],
    tags: list[str],
) -> dict[str, Any]:
    """Build the LangGraph invocation config, including LangSmith trace metadata.

    Args:
        thread_id: The checkpoint thread id.
        run_name: The human-readable run name shown in LangSmith.
        metadata: Structured metadata attached to the trace.
        tags: Tags attached to the trace.

    Returns:
        A config dict for ``graph.invoke`` / ``graph.stream``.
    """
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": run_name,
        "metadata": metadata,
        "tags": tags,
    }
