"""RunLog — the sole owner of the per-run JSONL trace format.

A run's trace is a JSONL file under ``logs/<slug>/<run_id>.jsonl``: one event per
line, ending in a terminal ``run.summary``. Every read and write of that format
lives here behind a small interface — :class:`RunTrace` appends events, and the
module functions locate, read, summarise, and tail a trace — so no caller
re-implements the line protocol or the terminal-event sentinel. The registry
(status inference), the runner (writing), and the API (listing and replaying)
all cross this one seam.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TERMINAL_EVENT = "run.summary"
_TAIL_POLL_SECONDS = 0.25


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
        self.event({"event": TERMINAL_EVENT, **data})

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


def read_events(path: Path) -> list[dict[str, Any]]:
    """Parse a trace file into its list of events, in file order.

    Args:
        path: The trace file to read.

    Returns:
        The parsed events, or an empty list when the file does not exist.
    """
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def terminal_summary(path: Path) -> dict[str, Any] | None:
    """Return the last ``run.summary`` event recorded in a trace, if any.

    Args:
        path: The trace file to scan.

    Returns:
        The terminal summary event, or ``None`` when the trace has no summary.
    """
    summary: dict[str, Any] | None = None
    for event in read_events(path):
        if event.get("event") == TERMINAL_EVENT:
            summary = event
    return summary


def find_trace(logs_dir: Path, run_id: str) -> Path | None:
    """Locate a run's JSONL trace across every slug's log directory.

    Args:
        logs_dir: The root of the ``logs/`` tree.
        run_id: The run id (trace filename without extension).

    Returns:
        The trace path, or ``None`` when no slug has a trace for the run id.
    """
    if not logs_dir.is_dir():
        return None
    for path in logs_dir.glob(f"*/{run_id}.jsonl"):
        return path
    return None


def list_run_ids(logs_dir: Path, slug: str) -> list[str]:
    """List the run ids traced for a slug, newest first.

    Args:
        logs_dir: The root of the ``logs/`` tree.
        slug: The campaign slug whose runs to list.

    Returns:
        The run ids (trace filenames without extension), newest first; empty when
        the slug has no log directory.
    """
    runs_dir = logs_dir / slug
    if not runs_dir.is_dir():
        return []
    return sorted((f.stem for f in runs_dir.glob("*.jsonl")), reverse=True)


async def tail_trace(
    path: Path,
    *,
    is_live: Callable[[], bool],
    poll_interval: float = _TAIL_POLL_SECONDS,
    terminal_event: str = TERMINAL_EVENT,
) -> AsyncIterator[dict[str, Any]]:
    """Follow a run's JSONL trace, yielding each event as it is appended.

    The reader counterpart of :class:`RunTrace`. Replays every event already written
    from the top of the file (so a late joiner sees the run from the start), then
    polls for appended lines and yields them as they arrive. The stream closes after
    the terminal ``run.summary`` event, or once the run is no longer live and the
    file has been fully drained — an interrupted run (a trace with no terminal
    summary and no live task) therefore replays and closes rather than polling
    forever.

    Only complete, newline-terminated lines are yielded, so a line still mid-write by
    the run is never emitted half-formed. Liveness is sampled *before* each read, so a
    run that finishes between reads is drained one final time before the stream ends;
    :class:`RunTrace` flushes and closes each event before the run deregisters, so the
    terminal summary is always on disk by the time ``is_live`` reports ``False``.

    Args:
        path: The run's ``.jsonl`` trace path. It may not exist yet for a run that has
            only just started; the tailer waits for it to appear while the run is live.
        is_live: Predicate returning whether the run is still executing.
        poll_interval: Seconds to sleep between reads while the run is live.
        terminal_event: The ``event`` value whose arrival closes the stream.

    Yields:
        Each trace event, in file order.
    """
    emitted = 0
    while True:
        was_live = is_live()
        if path.is_file():
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            complete = [line for line in lines if line.endswith("\n")]
            for line in complete[emitted:]:
                emitted += 1
                event = json.loads(line)
                yield event
                if event.get("event") == terminal_event:
                    return
        if not was_live:
            return
        await asyncio.sleep(poll_interval)
