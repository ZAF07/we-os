"""ADK callbacks that enforce guardrails and capture the per-step decision trace.

These are the live enforcement points (verified against ADK 2.3 signatures):

- ``after_model_callback(ctx, llm_response)`` — after each model turn: parse the
  agent's DecisionEnvelope (if present), run the cheap hard-guardrail
  `scan_output`, and record both into session state (and an optional live sink).
  Returns ``None`` (annotate, don't rewrite — the Evaluator is the formal gate).
- ``before_tool_callback(tool, args, ctx)`` — before each tool call: log it and,
  as defense-in-depth, deny any tool not on the agent's allowlist (the allowlist
  is normally enforced by simply not attaching the tool).

Captured data lives in ``ctx.state`` under ``steps`` / ``violations`` so it flows
to downstream agents and is persisted to long-term memory at run end.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from ..schemas import DecisionEnvelope
from .hard import scan_output

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)

StepSink = Callable[[dict], None]


def _text_of(llm_response: Any) -> str:
    """Concatenate the text parts of an LlmResponse (empty on tool-only turns)."""
    content = getattr(llm_response, "content", None)
    parts = getattr(content, "parts", None) or []
    return "".join(getattr(p, "text", "") or "" for p in parts).strip()


def _extract_envelope(text: str) -> Optional[dict]:
    """Best-effort parse of the agent's DecisionEnvelope from its output text.

    Looks for a fenced ```json block first, then a bare leading object. Returns the
    validated envelope as a dict, or None if absent/invalid (which is fine — not
    every turn carries one).
    """
    candidate: Optional[str] = None
    m = _JSON_BLOCK_RE.search(text)
    if m:
        candidate = m.group(1)
    elif text.startswith("{"):
        depth = 0
        for i, ch in enumerate(text):
            depth += ch == "{"
            depth -= ch == "}"
            if depth == 0:
                candidate = text[: i + 1]
                break
    if not candidate:
        return None
    try:
        return DecisionEnvelope.model_validate_json(candidate).model_dump(mode="json")
    except Exception:
        return None


def build_callbacks(stage_key: str, on_step: Optional[StepSink] = None) -> dict:
    """Build the guardrail callbacks for one stage's worker agent.

    Args:
        stage_key: Pipeline stage these callbacks belong to (tags the captured trace).
        on_step: Optional live sink (e.g. CLI printer / SSE emitter) called with each
            captured step event.

    Returns:
        A dict to splat into ``LlmAgent(**build_callbacks(...))`` —
        ``{"after_model_callback": ..., "before_tool_callback": ...}``.
    """

    def after_model_callback(callback_context: Any, llm_response: Any):
        """Capture the decision envelope + scan output against the hard floor.

        ADK invokes this as ``after_model_callback(callback_context=, llm_response=)``,
        so the parameter names must match exactly.
        """
        text = _text_of(llm_response)
        envelope = _extract_envelope(text)
        violations = scan_output(text, stage_key)

        steps = list(callback_context.state.get("steps", []))
        record = {
            "stage": stage_key,
            "agent": getattr(callback_context, "agent_name", None),
            "envelope": envelope,
            "violations": violations,
            "text_preview": text[:280],
        }
        steps.append(record)
        callback_context.state["steps"] = steps
        if violations:
            existing = list(callback_context.state.get("violations", []))
            existing.extend(violations)
            callback_context.state["violations"] = existing
        if on_step:
            on_step(record)
        return None  # annotate only; never rewrite the model output here

    def before_tool_callback(tool: Any, args: dict, tool_context: Any):
        """Log the tool call (allowlist is enforced by tool attachment upstream).

        ADK invokes this as ``before_tool_callback(tool=, args=, tool_context=)``,
        so the parameter names must match exactly.
        """
        calls = list(tool_context.state.get("tool_calls", []))
        calls.append({"stage": stage_key, "tool": getattr(tool, "name", str(tool)), "args": args})
        tool_context.state["tool_calls"] = calls
        return None  # proceed with the call

    return {
        "after_model_callback": after_model_callback,
        "before_tool_callback": before_tool_callback,
    }
