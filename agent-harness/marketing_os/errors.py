"""Typed exception hierarchy for the Marketing OS harness.

Each failure mode has a distinct type so callers (CLI, API, tests) can tell a
governance block apart from a guardrail violation apart from a paused approval.
"""

from __future__ import annotations


class MarketingOSError(Exception):
    """Base class for every error raised by the harness."""


class ConfigError(MarketingOSError):
    """Settings are missing or invalid (e.g. no API key for the active provider)."""


class GateError(MarketingOSError):
    """Stage 0 gate failed: Customer DNA or campaign goal is missing/incomplete.

    Args:
        message: Human-readable explanation.
        missing: The structured list of offending field issues, for the caller to
            relay to the operator verbatim.
    """

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing: list[str] = missing or []


class GuardrailError(MarketingOSError):
    """A deliverable violated the non-editable hard guardrails and could not be
    reconciled within the allowed evaluator iterations."""

    def __init__(self, message: str, violations: list | None = None) -> None:
        super().__init__(message)
        self.violations = violations or []


class ApprovalRequired(MarketingOSError):
    """A human approval gate paused the run.

    Raised (or surfaced as an event) when a tool/stage configured for human
    review is reached. Carries the pending-approval id so the caller can resume.

    Args:
        message: What needs approving.
        approval_id: Opaque id the caller passes back to resume the run.
        payload: Context shown to the human (stage, deliverable path, risk, etc.).
    """

    def __init__(self, message: str, approval_id: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.approval_id = approval_id
        self.payload = payload or {}


class ToolError(MarketingOSError):
    """A tool could not run (bad arguments, sandbox violation, backend failure).

    Tool failures are usually returned to the model as an error result rather than
    raised; this is for cases the harness itself must reject.
    """


class ModelError(MarketingOSError):
    """The configured LLM/provider could not be constructed or invoked."""
