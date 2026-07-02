"""QA reviewer: rubric assembly and structured-output verdicts with fallback."""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.review import LLMReviewer
from marketing_os.governance import load_rubric
from marketing_os.schemas import Discrepancy, ReviewVerdict


class _StructuredStub:
    """Returns a scripted verdict or raises to exercise the fallback."""

    def __init__(self, result: Any) -> None:
        self._result = result

    def invoke(self, messages: Any, config: Any = None) -> ReviewVerdict:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeStructuredModel:
    """A model whose structured-output binding yields a scripted stub."""

    def __init__(self, result: Any) -> None:
        self._result = result

    def with_structured_output(self, schema: Any) -> _StructuredStub:
        return _StructuredStub(self._result)


def test_load_rubric_includes_shared_and_stage(settings):
    rubric = load_rubric(settings, "research")
    assert "DNA-grounded" in rubric
    assert "customer/competitor/market" in rubric
    assert "Operating Principles" in rubric


def test_reviewer_pass(settings):
    model = _FakeStructuredModel(ReviewVerdict(passed=True, summary="ok"))
    verdict = LLMReviewer(model, settings).review("research", "some deliverable")
    assert verdict.passed
    assert verdict.discrepancies == []


def test_reviewer_fail_with_discrepancies(settings):
    result = ReviewVerdict(
        passed=False,
        summary="missing competitors",
        discrepancies=[
            Discrepancy(
                rubric_point="competitor research",
                problem="no competitors named",
                fix="name them",
            )
        ],
    )
    verdict = LLMReviewer(_FakeStructuredModel(result), settings).review("research", "d")
    assert not verdict.passed
    assert verdict.discrepancies[0].rubric_point == "competitor research"
    assert "no competitors named" in verdict.as_revision_instruction()


def test_reviewer_unparseable_fails_closed(settings):
    model = _FakeStructuredModel(ValueError("model returned junk"))
    verdict = LLMReviewer(model, settings).review("research", "deliverable")
    assert not verdict.passed
    assert verdict.discrepancies[0].rubric_point == "review-format"
