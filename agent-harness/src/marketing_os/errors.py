"""Exception hierarchy for the Marketing OS harness.

Every failure mode the pipeline can hit has a typed exception so callers (CLI,
API, tests) can distinguish a governance block from a provider outage from a
tool sandbox violation.
"""

from __future__ import annotations

from typing import Any


class MarketingOSError(Exception):
    """Base class for every error raised by the harness.

    Each subclass carries its own presentation — the HTTP status an entrypoint
    maps it to and the process exit code — so callers dispatch on the type rather
    than re-deciding the mapping at every seam.

    Attributes:
        detail: An optional structured payload (stage, discrepancies, …) the API
            returns to the client; populated by the runner for run failures.
        run_log: An optional repo-relative path to the run's JSONL trace.
        http_status: The HTTP status code an API entrypoint returns for this error.
        exit_code: The process exit code a CLI entrypoint returns for this error.
    """

    detail: dict[str, Any] | None = None
    run_log: str | None = None
    http_status: int = 500
    exit_code: int = 1


class ConfigError(MarketingOSError):
    """Settings are missing or invalid (e.g. no API key for the active provider)."""

    http_status = 500


class GateError(MarketingOSError):
    """Stage 0 gate failed: Customer DNA or campaign goal is missing/incomplete.

    Carries the structured list of offending fields so the caller can tell the
    operator exactly what to fix.
    """

    http_status = 409

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        """Initialise the error.

        Args:
            message: The human-readable message.
            missing: The offending DNA or goal fields, if known.
        """
        super().__init__(message)
        self.missing: list[str] = missing or []
        self.detail = {"type": "gate", "message": message, "issues": self.missing}


class RunConflictError(MarketingOSError):
    """A run was requested for a slug that already has an active run.

    At most one run per slug may be active at a time (both full-pipeline and
    single-stage runs write into ``campaigns/<slug>/``), so a second request is
    rejected. Carries the ``run_id`` of the run already in flight.
    """

    http_status = 409

    def __init__(self, slug: str, active_run_id: str) -> None:
        """Initialise the error.

        Args:
            slug: The campaign slug that already has an active run.
            active_run_id: The id of the run already in flight for the slug.
        """
        message = f"Campaign '{slug}' already has an active run '{active_run_id}'."
        super().__init__(message)
        self.slug = slug
        self.active_run_id = active_run_id
        self.detail = {
            "type": "slug_busy",
            "message": message,
            "active_run_id": active_run_id,
        }


class PipelineError(MarketingOSError):
    """A stage was started out of order or its prerequisite deliverable is absent."""

    http_status = 409


class GuardrailError(MarketingOSError):
    """A deliverable failed QA review within the allowed self-critique budget.

    Carries the unresolved discrepancies so the caller can report them.
    """

    http_status = 422

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

    http_status = 502


class ProviderError(MarketingOSError):
    """An LLM provider adapter failed in a way the SDK's own retries did not cover."""

    http_status = 502


def exception_from_state_error(error: dict[str, Any], run_log: str | None) -> MarketingOSError:
    """Translate a halting graph-state error dict into a typed exception.

    The graph records why a run halted as a plain, JSON-serialisable dict on
    ``state["error"]`` (its ``type`` is one of ``gate`` / ``pipeline`` / ``save`` /
    ``guardrail``). This is the one place that maps those strings to the typed
    exception hierarchy, building the human message and the structured ``detail``
    payload once so no entrypoint re-encodes the taxonomy.

    Args:
        error: The ``state["error"]`` dict describing the halt.
        run_log: The repo-relative path of the run's JSONL trace, if any.

    Returns:
        The typed exception for the halt, with ``detail`` and ``run_log`` set.
    """
    kind = error.get("type")
    stage = error.get("stage")
    exc: MarketingOSError
    if kind == "gate":
        issues = [str(issue) for issue in error.get("issues", [])]
        message = "Stage 0 gate failed: " + "; ".join(issues)
        exc = GateError(message, missing=issues)
        detail: dict[str, Any] = {"message": message, "issues": issues}
    elif kind == "pipeline":
        message = (
            f"Stage '{stage}' cannot start: prerequisite "
            f"'{error.get('prerequisite')}' does not exist."
        )
        exc = PipelineError(message)
        detail = {"message": message, "prerequisite": error.get("prerequisite")}
    elif kind == "save":
        message = f"Stage '{stage}' did not save its deliverable to {error.get('deliverable')}."
        exc = PipelineError(message)
        detail = {"message": message, "deliverable": error.get("deliverable")}
    elif kind == "guardrail":
        message = f"Stage '{stage}' failed QA and could not be reconciled."
        exc = GuardrailError(message, discrepancies=error.get("discrepancies", []))
        detail = {
            "message": message,
            "summary": error.get("summary"),
            "discrepancies": error.get("discrepancies", []),
        }
    else:
        message = f"Run halted: {error}"
        exc = PipelineError(message)
        detail = {"message": message}
    detail.update({"type": kind, "stage": stage, "run_log": run_log})
    exc.detail = detail
    exc.run_log = run_log
    return exc
