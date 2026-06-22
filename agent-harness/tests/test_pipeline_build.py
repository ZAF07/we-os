"""ADK graph assembly + the evaluator escalation gate (no live model calls)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from marketing_os.agents import BuildContext, EscalationGate, build_evaluator, load_registry
from marketing_os.governance.rules import load_governance
from marketing_os.model import build_model
from marketing_os.pipeline import DELIVERABLE_KEYS, build_coordinator
from marketing_os.tools import FilesystemTools, WebBrowser


def _ctx(settings) -> BuildContext:
    return BuildContext(
        settings=settings,
        model=build_model(settings),  # constructs LiteLlm; no network at build time
        governance=load_governance(settings),
        registry=load_registry(settings),
        fs=FilesystemTools(settings.root),
        browser=WebBrowser(),
    )


def test_coordinator_graph_shape(settings):
    coord = build_coordinator(_ctx(settings))
    assert coord.name == "marketing_coordinator"
    top = [a.name for a in coord.sub_agents]
    # intake precedes the loop; execution/performance follow (approval off by default)
    assert top == ["intake_stage", "refine_loop", "execution_stage", "performance_stage"]

    refine = next(a for a in coord.sub_agents if a.name == "refine_loop")
    loop_children = [a.name for a in refine.sub_agents]
    # The six .claude stages run in canonical order inside the loop, then the gate.
    assert loop_children == [
        "research_stage",
        "strategy_stage",
        "campaign_strategy_stage",
        "creative_stage",
        "asset_prompts_stage",
        "media_stage",
        "evaluator",
        "eval_gate",
    ]
    assert refine.max_iterations == settings.max_eval_iterations


def test_resume_skip_guards_on_linear_stages_only(settings):
    coord = build_coordinator(_ctx(settings))
    by_name = {a.name: a for a in coord.sub_agents}
    # Linear top-level stages + the refine loop carry a resume skip guard.
    for name in ["intake_stage", "execution_stage", "performance_stage", "refine_loop"]:
        assert by_name[name].before_agent_callback, f"{name} should have a skip guard"
    # Stages INSIDE the refine loop must NOT skip (they re-run each iteration).
    refine = by_name["refine_loop"]
    for child in ["research_stage", "strategy_stage", "campaign_strategy_stage"]:
        stage = next(a for a in refine.sub_agents if a.name == child)
        assert not stage.before_agent_callback


def test_each_stage_is_worker_plus_formatter(settings):
    coord = build_coordinator(_ctx(settings))
    intake = next(a for a in coord.sub_agents if a.name == "intake_stage")
    assert [a.name for a in intake.sub_agents] == ["intake_worker", "intake_formatter"]
    # formatter carries the strict output schema; worker carries tools.
    worker, formatter = intake.sub_agents
    assert formatter.output_schema is not None
    assert worker.output_schema is None
    assert worker.output_key == "intake_raw" and formatter.output_key == "intake"
    # The formatter reads the worker's output via the OPTIONAL template form, so a
    # missing/empty output_key degrades gracefully instead of raising KeyError.
    assert "{intake_raw?}" in formatter.instruction
    # Workers are required to emit the full deliverable as final text so output_key fills.
    assert "Final output (required)" in worker.instruction


def test_formatter_provider_aware_structured_output(settings):
    # Gemini-style (supports output_schema): formatter uses constrained decoding.
    ctx = _ctx(settings)  # default structured_output=True
    fmt = build_coordinator(ctx).sub_agents[0].sub_agents[1]  # intake_formatter
    assert fmt.output_schema is not None
    assert "JSON Schema:" not in fmt.instruction

    # DeepSeek-style (no JSON-schema response_format): no output_schema; schema is
    # embedded in the prompt instead, so the provider never sees response_format.
    from marketing_os.agents import BuildContext
    from marketing_os.governance.rules import load_governance
    from marketing_os.agents import load_registry
    from marketing_os.tools import FilesystemTools, WebBrowser

    ds = BuildContext(
        settings=settings, model=build_model(settings, "deepseek"),
        governance=load_governance(settings), registry=load_registry(settings),
        fs=FilesystemTools(settings.root), browser=WebBrowser(), structured_output=False,
    )
    fmt2 = build_coordinator(ds).sub_agents[0].sub_agents[1]
    assert fmt2.output_schema is None
    assert "JSON Schema:" in fmt2.instruction


def test_evaluator_has_schema_and_no_tools(settings):
    ev = build_evaluator(_ctx(settings))
    assert ev.output_schema.__name__ == "EvalReport"
    assert ev.output_key == "eval"
    assert not ev.tools


def test_deliverable_keys_match_stage_outputs():
    assert DELIVERABLE_KEYS == [
        "intake",
        "research",
        "strategy",
        "campaign_strategy",
        "creative",
        "asset_prompts",
        "media",
        "eval",
        "execution",
        "performance",
    ]


async def test_escalation_gate_escalates_only_when_eval_passed():
    gate = EscalationGate(name="eval_gate")

    passed_ctx = SimpleNamespace(session=SimpleNamespace(state={"eval": {"passed": True}}))
    events = [e async for e in gate._run_async_impl(passed_ctx)]
    assert len(events) == 1 and events[0].actions.escalate is True

    failed_ctx = SimpleNamespace(session=SimpleNamespace(state={"eval": {"passed": False}}))
    events = [e async for e in gate._run_async_impl(failed_ctx)]
    assert events == []  # no escalation -> loop continues
