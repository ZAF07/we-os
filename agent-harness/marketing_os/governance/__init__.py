"""Governance: the Stage-0 gate and the rules preamble.

The pipeline graph itself now lives in `marketing_os.agents` (ADK agents) and is
assembled in `marketing_os.pipeline`; the editable review rubrics live in
`marketing_os.guardrails`.
"""

from __future__ import annotations

from .gate import (
    GateReport,
    check_gate,
    enforce_gate,
    required_fields,
    validate_document,
)
from .rules import load_governance, load_operating_principles

__all__ = [
    "GateReport",
    "check_gate",
    "enforce_gate",
    "required_fields",
    "validate_document",
    "load_governance",
    "load_operating_principles",
]
