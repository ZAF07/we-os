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
    maps it to, the ``type`` discriminator the frozen API contract names it by,
    and the process exit code — so callers dispatch on the type rather than
    re-deciding the mapping at every seam.

    Attributes:
        detail: An optional structured payload (stage, discrepancies, …) the API
            returns to the client; populated by the runner for run failures.
        run_log: An optional repo-relative path to the run's JSONL trace.
        http_status: The HTTP status code an API entrypoint returns for this error.
        error_type: The contract's ``Error.type`` discriminator for this error.
        exit_code: The process exit code a CLI entrypoint returns for this error.
    """

    detail: dict[str, Any] | None = None
    run_log: str | None = None
    http_status: int = 500
    error_type: str = "internal"
    exit_code: int = 1


class ConfigError(MarketingOSError):
    """Settings are missing or invalid (e.g. no API key for the active provider)."""

    http_status = 500
    error_type = "internal"


class UnauthenticatedError(MarketingOSError):
    """The request carried no identity, or one that did not verify.

    Raised by the token verifier for every failure mode — absent, malformed,
    expired, wrongly signed, wrong issuer or audience, or carrying no tenant
    claim. The reasons are deliberately not distinguished to the caller, so a
    probe learns nothing about why a token was refused.
    """

    http_status = 401
    error_type = "unauthenticated"


class GateError(MarketingOSError):
    """Stage 0 gate failed: Brand DNA or campaign goal is missing/incomplete.

    Carries the structured list of offending fields so the caller can tell the
    operator exactly what to fix.
    """

    http_status = 409
    error_type = "gate_failed"

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        """Initialise the error.

        Args:
            message: The human-readable message.
            missing: The offending DNA or goal fields, if known.
        """
        super().__init__(message)
        self.missing: list[str] = missing or []
        self.detail = {
            "type": self.error_type,
            "status": self.http_status,
            "message": message,
            "missing_fields": self.missing,
        }


class RunConflictError(MarketingOSError):
    """A run was requested for a campaign someone is already running.

    At most one run per campaign may be active at a time — both full-pipeline
    and single-stage runs write into ``campaigns/<slug>/`` — and that run
    belongs to the person who started it. A colleague in the same business is
    refused too, and told so plainly: two people driving one campaign would
    overwrite each other's deliverables.
    """

    http_status = 409
    error_type = "run_conflict"

    def __init__(self, slug: str, active_run_id: str, active_user_id: str = "") -> None:
        """Initialise the error.

        Args:
            slug: The campaign that already has an active run.
            active_run_id: The id of the run already in flight.
            active_user_id: The user who started it, when known, so the caller
                is told a colleague is working on it rather than left guessing.
        """
        message = f"Campaign '{slug}' already has an active run '{active_run_id}'."
        if active_user_id:
            message = (
                f"Campaign '{slug}' is being run by someone else in your business "
                f"(run '{active_run_id}'). Wait for it to finish, or ask them to cancel it."
            )
        super().__init__(message)
        self.slug = slug
        self.active_run_id = active_run_id
        self.active_user_id = active_user_id
        self.detail = {
            "type": self.error_type,
            "status": self.http_status,
            "message": message,
            "active_run_id": active_run_id,
            "active_user_id": active_user_id,
        }


class PipelineError(MarketingOSError):
    """A stage was started out of order or its prerequisite deliverable is absent."""

    http_status = 409
    error_type = "validation"


class GuardrailError(MarketingOSError):
    """A deliverable failed QA review within the allowed self-critique budget.

    Carries the unresolved discrepancies so the caller can report them.
    """

    http_status = 422
    error_type = "validation"

    def __init__(self, message: str, discrepancies: list | None = None) -> None:
        """Initialise the error.

        Args:
            message: The human-readable message.
            discrepancies: The unresolved QA discrepancies, if known.
        """
        super().__init__(message)
        self.discrepancies = discrepancies or []


class DocumentNotFoundError(MarketingOSError):
    """A requested document does not exist in the document store for the tenant.

    A document belonging to another tenant raises this too: cross-tenant access
    is indistinguishable from absence, so nothing leaks across the boundary.
    """

    http_status = 404
    error_type = "not_found"


class ToolError(MarketingOSError):
    """A tool could not run (bad arguments, sandbox violation, backend failure).

    Tool errors are usually returned to the model as an error tool-result rather
    than raised — this is for the cases the harness itself must reject.
    """

    http_status = 502
    error_type = "internal"


class ProviderError(MarketingOSError):
    """An LLM provider adapter failed in a way the SDK's own retries did not cover."""

    http_status = 502
    error_type = "internal"


def exception_from_state_error(error: dict[str, Any], run_log: str | None) -> MarketingOSError:
    """Translate a halting graph-state error dict into a typed exception.

    The graph records why a run halted as a plain, JSON-serialisable dict on
    ``state["error"]`` (its ``type`` is one of ``gate`` / ``pipeline`` / ``save`` /
    ``guardrail``). Those are the graph's internal discriminators; the ``type``
    on the returned payload is the exception's ``error_type``, which is the name
    the frozen API contract uses. This is the one place that maps between them,
    building the human message and the structured ``detail`` payload once so no
    entrypoint re-encodes the taxonomy.

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
    detail.update(
        {
            "type": exc.error_type,
            "status": exc.http_status,
            "halt_reason": kind,
            "stage": stage,
            "run_log": run_log,
        }
    )
    exc.detail = detail
    exc.run_log = run_log
    return exc
