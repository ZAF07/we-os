"""Observability adapter — local logging, run traces, and LangSmith tracing.

Three concerns live here, all driven off the semantic events the graph already
emits:

* :func:`configure_logging` sets up stdlib logging so a developer sees a run live
  on the console.
* :class:`RunTrace` appends a structured JSONL trace per run under ``logs/`` so a
  finished (or failed) run can be inspected afterwards.
* :func:`configure_tracing` turns on LangChain's native LangSmith tracing (the
  primary deep prompt/tool/response surface) when its environment is present.

Content is metadata-level by design: events, verdicts, and discrepancies are
recorded, but raw prompts and full deliverable text are not.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from marketing_os.config import Settings

_LOGGER_NAME = "marketing_os"
_TRACING_ENV_VARS = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")
_DEFAULT_PROJECT = "marketing-os"


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return a logger under the ``marketing_os`` namespace.

    Args:
        name: The logger name; defaults to the package logger.

    Returns:
        The requested logger.
    """
    return logging.getLogger(name)


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure console logging for the harness (idempotent).

    Args:
        settings: The harness settings supplying the log level.

    Returns:
        The configured package logger.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    if not any(getattr(h, "_marketing_os", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
        )
        handler._marketing_os = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger


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


class RunTrace:
    """Appends a structured JSONL trace of one run under the ``logs/`` tree."""

    def __init__(self, path: Path) -> None:
        """Open the trace file, creating parent directories.

        Args:
            path: The destination ``.jsonl`` path.
        """
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")

    def event(self, data: dict[str, Any]) -> None:
        """Append one timestamped event line.

        Args:
            data: The event payload (must be JSON-serialisable).
        """
        self._write({"ts": datetime.now(UTC).isoformat(), **data})

    def summary(self, **data: Any) -> None:
        """Append the terminal ``run.summary`` line.

        Args:
            **data: The summary payload (outcome, results, usage).
        """
        self.event({"event": "run.summary", **data})

    def _write(self, record: dict[str, Any]) -> None:
        """Write one JSON record and flush.

        Args:
            record: The record to serialise.
        """
        self._handle.write(json.dumps(record, default=str) + "\n")
        self._handle.flush()

    def close(self) -> None:
        """Close the underlying file handle."""
        if not self._handle.closed:
            self._handle.close()

    def __enter__(self) -> RunTrace:
        """Enter the context manager.

        Returns:
            This trace instance.
        """
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the trace on context exit.

        Args:
            *exc: Unused exception information.
        """
        self.close()
