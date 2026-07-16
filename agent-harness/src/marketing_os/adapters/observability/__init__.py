"""Observability — console logging, LangSmith tracing, and per-run JSONL traces.

Three cohesive concerns, one per submodule:

* :mod:`console` — stdlib console logging (:func:`get_logger`,
  :func:`configure_logging`).
* :mod:`tracing` — LangSmith activation and per-run invocation config
  (:func:`configure_tracing`, :func:`new_run_id`, :func:`run_config`).
* :mod:`runlog` — the sole owner of the JSONL trace format: :class:`RunTrace`
  writes it, and the reader functions locate, parse, summarise, and tail it.

The names are re-exported here so callers depend on the package, not the split.
Content is metadata-level by design: events, verdicts, and discrepancies are
recorded, but raw prompts and full deliverable text are not.
"""

from __future__ import annotations

from marketing_os.adapters.observability.console import configure_logging, get_logger
from marketing_os.adapters.observability.runlog import (
    RunTrace,
    find_trace,
    list_run_ids,
    read_events,
    tail_trace,
    terminal_summary,
)
from marketing_os.adapters.observability.tracing import (
    configure_tracing,
    new_run_id,
    run_config,
    tracing_enabled,
)

__all__ = [
    "get_logger",
    "configure_logging",
    "configure_tracing",
    "tracing_enabled",
    "new_run_id",
    "run_config",
    "RunTrace",
    "tail_trace",
    "read_events",
    "terminal_summary",
    "find_trace",
    "list_run_ids",
]
