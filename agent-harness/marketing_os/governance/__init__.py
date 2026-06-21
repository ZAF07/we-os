"""Governance: rules preamble, Stage 0 gate, the pipeline, and the QA reviewer."""

from __future__ import annotations

from .gate import GateReport, check_gate, enforce_gate, required_fields, validate_document
from .pipeline import DIRECTOR, PIPELINE, PIPELINE_BY_KEY, Stage, deliverable_path, prerequisite_met
from .review import Reviewer, load_rubric
from .rules import load_governance, load_operating_principles

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
    "Reviewer",
    "load_rubric",
]
