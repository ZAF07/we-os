"""Error taxonomy: typed presentation and the one state-error → exception map.

These lock the single crossing that :func:`exception_from_state_error` owns —
graph-state error dicts become typed exceptions with their message, structured
``detail``, and ``run_log`` — plus the per-type HTTP status and exit code the
entrypoints dispatch on instead of re-encoding the taxonomy.
"""

from __future__ import annotations

from marketing_os.errors import (
    GateError,
    GuardrailError,
    PipelineError,
    RunConflictError,
    exception_from_state_error,
)


def test_gate_state_error_maps_to_gate_error() -> None:
    exc = exception_from_state_error(
        {"type": "gate", "issues": ["DNA: missing name"]}, run_log="logs/acme/r.jsonl"
    )
    assert isinstance(exc, GateError)
    assert exc.http_status == 409
    assert exc.detail is not None
    assert exc.detail["type"] == "gate"
    assert exc.detail["issues"] == ["DNA: missing name"]
    assert exc.run_log == "logs/acme/r.jsonl"


def test_pipeline_and_save_state_errors_map_to_pipeline_error() -> None:
    prereq = exception_from_state_error(
        {"type": "pipeline", "stage": "brand-strategy", "prerequisite": "research.md"}, None
    )
    save = exception_from_state_error(
        {"type": "save", "stage": "research", "deliverable": "campaigns/acme/research.md"}, None
    )
    assert isinstance(prereq, PipelineError)
    assert prereq.detail is not None and prereq.detail["prerequisite"] == "research.md"
    assert isinstance(save, PipelineError)
    assert save.detail is not None and save.detail["deliverable"] == "campaigns/acme/research.md"


def test_guardrail_state_error_carries_typed_discrepancies() -> None:
    discrepancies = [{"rubric_point": "coverage", "problem": "no competitors", "fix": "add"}]
    exc = exception_from_state_error(
        {
            "type": "guardrail",
            "stage": "research",
            "summary": "too thin",
            "discrepancies": discrepancies,
        },
        run_log="logs/acme/r.jsonl",
    )
    assert isinstance(exc, GuardrailError)
    assert exc.http_status == 422
    assert exc.discrepancies == discrepancies
    assert exc.detail is not None and exc.detail["discrepancies"] == discrepancies


def test_run_conflict_error_is_self_describing() -> None:
    exc = RunConflictError("acme", "20260716T101010Z-abcd1234")
    assert exc.http_status == 409
    assert exc.detail is not None
    assert exc.detail["type"] == "slug_busy"
    assert exc.detail["active_run_id"] == "20260716T101010Z-abcd1234"
