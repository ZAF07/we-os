"""QA reviewer: rubric assembly + verdict parsing (pass / fail / unparseable)."""

from __future__ import annotations

import json

from marketing_os.governance import Reviewer, load_rubric

from conftest import FakeProvider


def test_load_rubric_includes_shared_and_stage(settings):
    rubric = load_rubric(settings, "research")
    assert "DNA-grounded" in rubric  # from shared.md
    assert "customer/competitor/market" in rubric  # from research.md
    assert "Operating Principles" in rubric  # from operating-principles.md


def test_reviewer_pass(settings):
    provider = FakeProvider([{"text": json.dumps({"passed": True, "summary": "ok", "discrepancies": []})}])
    verdict = Reviewer(provider, settings).review("research", "some deliverable")
    assert verdict.passed
    assert verdict.discrepancies == []


def test_reviewer_fail_with_discrepancies(settings):
    payload = {
        "passed": False,
        "summary": "missing competitors",
        "discrepancies": [
            {"rubric_point": "competitor research", "problem": "no competitors named", "fix": "name them"}
        ],
    }
    provider = FakeProvider([{"text": "Here is my verdict:\n" + json.dumps(payload)}])
    verdict = Reviewer(provider, settings).review("research", "deliverable")
    assert not verdict.passed
    assert verdict.discrepancies[0].rubric_point == "competitor research"
    # The revision instruction surfaces the problem to the specialist.
    assert "no competitors named" in verdict.as_revision_instruction()


def test_reviewer_unparseable_fails_closed(settings):
    provider = FakeProvider([{"text": "I think it looks fine, no JSON here."}])
    verdict = Reviewer(provider, settings).review("research", "deliverable")
    assert not verdict.passed
    assert verdict.discrepancies[0].rubric_point == "review-format"
