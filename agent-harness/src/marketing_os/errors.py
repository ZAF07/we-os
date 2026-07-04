"""Exception hierarchy for the Marketing OS harness.

Every failure mode the pipeline can hit has a typed exception so callers (CLI,
API, tests) can distinguish a governance block from a provider outage from a
tool sandbox violation.
"""

from __future__ import annotations

from typing import Any


class MarketingOSError(Exception):
    """Base class for every error raised by the harness.

    Attributes:
        detail: An optional structured payload (stage, discrepancies, …) the API
            returns to the client; populated by the runner for run failures.
        run_log: An optional repo-relative path to the run's JSONL trace.
    """

    detail: dict[str, Any] | None = None
    run_log: str | None = None


class ConfigError(MarketingOSError):
    """Settings are missing or invalid (e.g. no API key for the active provider)."""


class GateError(MarketingOSError):
    """Stage 0 gate failed: Customer DNA or campaign goal is missing/incomplete.

    Carries the structured list of offending fields so the caller can tell the
    operator exactly what to fix.
    """

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        """Initialise the error.

        Args:
            message: The human-readable message.
            missing: The offending DNA or goal fields, if known.
        """
        super().__init__(message)
        self.missing: list[str] = missing or []


class RunConflictError(MarketingOSError):
    """A run was requested for a slug that already has an active run.

    At most one run per slug may be active at a time (both full-pipeline and
    single-stage runs write into ``campaigns/<slug>/``), so a second request is
    rejected. Carries the ``run_id`` of the run already in flight.
    """

    def __init__(self, slug: str, active_run_id: str) -> None:
        """Initialise the error.

        Args:
            slug: The campaign slug that already has an active run.
            active_run_id: The id of the run already in flight for the slug.
        """
        super().__init__(f"Campaign '{slug}' already has an active run '{active_run_id}'.")
        self.slug = slug
        self.active_run_id = active_run_id


class PipelineError(MarketingOSError):
    """A stage was started out of order or its prerequisite deliverable is absent."""


class GuardrailError(MarketingOSError):
    """A deliverable failed QA review within the allowed self-critique budget.

    Carries the unresolved discrepancies so the caller can report them.
    """

    def __init__(self, message: str, discrepancies: list | None = None) -> None:
        """Initialise the error.

        Args:
            message: The human-readable message.
            discrepancies: The unresolved QA discrepancies, if known.
        """
        super().__init__(message)
        self.discrepancies = discrepancies or []


class ToolError(MarketingOSError):
    """A tool could not run (bad arguments, sandbox violation, backend failure).

    Tool errors are usually returned to the model as an error tool-result rather
    than raised — this is for the cases the harness itself must reject.
    """


class ProviderError(MarketingOSError):
    """An LLM provider adapter failed in a way the SDK's own retries did not cover."""
