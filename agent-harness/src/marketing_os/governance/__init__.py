"""Governance: rules preamble, Stage 0 gate, the pipeline, and rubric assembly."""

from __future__ import annotations

from marketing_os.governance.gate import (
    GateReport,
    check_gate,
    enforce_gate,
    required_fields,
    validate_document,
)
from marketing_os.governance.pipeline import (
    DIRECTOR,
    PIPELINE,
    PIPELINE_BY_KEY,
    Stage,
    deliverable_path,
    prerequisite_met,
)
from marketing_os.governance.rubric import load_rubric
from marketing_os.governance.rules import load_governance, load_operating_principles

__all__ = [
    "load_governance",
    "load_operating_principles",
    "GateReport",
    "check_gate",
    "enforce_gate",
    "required_fields",
    "validate_document",
    "PIPELINE",
    "PIPELINE_BY_KEY",
    "Stage",
    "DIRECTOR",
    "deliverable_path",
    "prerequisite_met",
    "load_rubric",
]
