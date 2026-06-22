"""Human-in-the-loop approval tool.

Implemented as an ADK `LongRunningFunctionTool`: when an agent calls it, the
function returns ``{"status": "pending", ...}`` and the run **pauses**. The
orchestrator detects the pending long-running call, surfaces it to a human (CLI
prompt or API `POST /approvals/{id}`), and resumes the run by sending back a
`FunctionResponse` carrying the human's decision.

This is opt-in per agent (see agents.yaml `human_check`); it is never attached
by default.
"""

from __future__ import annotations

from google.adk.tools import LongRunningFunctionTool

#: The tool name agents call; the orchestrator matches pending calls by this name.
APPROVAL_TOOL_NAME = "request_human_approval"


def request_human_approval(summary: str, details: str = "", risk_level: str = "medium") -> dict:
    """Request a human's approval before proceeding; pauses the run until answered.

    Call this when your work is ready for sign-off, or when your decision
    envelope sets ``requires_approval`` / a high ``risk_level``.

    Args:
        summary: One line describing what needs approval (e.g. "Approve strategy").
        details: Optional context for the reviewer (key risks, what changes if rejected).
        risk_level: "low" | "medium" | "high" — shown to the reviewer.

    Returns:
        While pending: {status:"pending", ...}. After the human resumes the run,
        ADK replaces this with the reviewer's decision
        ({status:"approved"|"rejected", comment?}).
    """
    return {"status": "pending", "summary": summary, "details": details, "risk_level": risk_level}


def approval_tool() -> LongRunningFunctionTool:
    """Build the long-running approval tool to attach to human-checked agents."""
    return LongRunningFunctionTool(func=request_human_approval)
