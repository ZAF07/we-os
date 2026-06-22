"""Two-tier guardrails: hard-floor scan, envelope capture, rubric assembly."""

from __future__ import annotations

from types import SimpleNamespace

from google.genai import types

from marketing_os.guardrails import HARD_GUARDRAILS, load_rubric, scan_output
from marketing_os.guardrails.callbacks import _extract_envelope, build_callbacks


def test_hard_floor_is_nonempty_text():
    assert "NON-NEGOTIABLE" in HARD_GUARDRAILS
    assert "never fabricate" in HARD_GUARDRAILS.lower()


def test_scan_flags_fabricated_stats_without_source():
    out = scan_output("The market grew 42% in 2024, then 18%, with 7% churn.", "strategy")
    assert out and "fabricated" in out[0].lower()


def test_scan_allows_sourced_stats():
    text = "Per the DNA, 40 memberships is the target (source: goal.md)."
    assert scan_output(text, "strategy") == []


def test_scan_flags_assets_in_pre_asset_stage():
    out = scan_output("Image prompt: a climber at dawn, Midjourney --ar 16:9", "strategy")
    assert out and "strategy-before-content" in out[0]


def test_scan_clean_strategy_passes():
    assert scan_output("We recommend coached intros because the DNA shows that drives signups.", "strategy") == []


def test_extract_envelope_from_fenced_json():
    text = (
        "```json\n"
        '{"thought_summary":"t","next_action":"web","tool_name":null,"tool_args":{},'
        '"reason":"r","expected_observation":"e","risk_level":"medium","requires_approval":true}'
        "\n```\nThen I will proceed."
    )
    env = _extract_envelope(text)
    assert env["risk_level"] == "medium" and env["requires_approval"] is True


def test_extract_envelope_none_when_absent():
    assert _extract_envelope("just prose, no json here") is None


def test_callbacks_match_adk_keyword_invocation():
    # ADK calls these with specific keyword names; the signatures must match
    # exactly (regression for the callback_context / tool_context kwargs).
    cbs = build_callbacks("strategy")
    state: dict = {}
    cc = SimpleNamespace(state=state, agent_name="strategy_worker")
    llm_response = SimpleNamespace(
        content=types.Content(role="model", parts=[types.Part(text="We recommend X because the DNA says Y.")])
    )
    assert cbs["after_model_callback"](callback_context=cc, llm_response=llm_response) is None
    assert state["steps"] and state["steps"][0]["stage"] == "strategy"

    tool = SimpleNamespace(name="write_file")
    assert cbs["before_tool_callback"](tool=tool, args={"path": "x"}, tool_context=cc) is None
    assert state["tool_calls"][0]["tool"] == "write_file"


def test_load_rubric_includes_shared_and_stage(settings):
    rubric = load_rubric(settings, "strategy")
    assert "Grounded in the DNA" in rubric  # from shared.md
    assert "distinct and defensible" in rubric  # from strategy.md
