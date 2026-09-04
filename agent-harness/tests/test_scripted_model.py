"""The scripted model: it must work for the suite, and be unreachable by accident."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from marketing_os.adapters.models import get_model
from marketing_os.adapters.scripted_model import (
    ENABLE_FLAG,
    PROVIDER_NAME,
    ScriptedChatModel,
    build_scripted_model,
)
from marketing_os.config import Settings
from marketing_os.errors import ConfigError
from marketing_os.governance.pipeline import PIPELINE
from marketing_os.schemas import ReviewVerdict


def test_it_refuses_to_build_unless_explicitly_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider that fabricates deliverables must never be reachable by accident."""
    monkeypatch.delenv(ENABLE_FLAG, raising=False)

    with pytest.raises(ConfigError) as raised:
        build_scripted_model()

    assert ENABLE_FLAG in str(raised.value)


def test_selecting_the_provider_is_not_enough_on_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Two deliberate settings, so one stray environment variable cannot do it."""
    monkeypatch.delenv(ENABLE_FLAG, raising=False)
    settings = Settings(root=tmp_path, provider=PROVIDER_NAME)

    with pytest.raises(ConfigError):
        get_model(settings)


def test_it_writes_the_deliverable_the_prompt_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One scripted model serves every stage by writing wherever it was asked to."""
    monkeypatch.setenv(ENABLE_FLAG, "1")
    model = build_scripted_model()

    result = model.invoke(
        [HumanMessage("Save the result to `campaigns/spring/brand-strategy.md`.")]
    )

    assert isinstance(result, AIMessage)
    assert result.tool_calls[0]["name"] == "write_file"
    assert result.tool_calls[0]["args"]["path"] == "campaigns/spring/brand-strategy.md"
    assert result.tool_calls[0]["args"]["content"].strip() != ""


def test_it_acknowledges_the_write_rather_than_looping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without this the specialist's inner loop would write forever."""
    monkeypatch.setenv(ENABLE_FLAG, "1")
    model = build_scripted_model()

    result = model.invoke(
        [
            HumanMessage("Save to `campaigns/spring/research.md`."),
            ToolMessage(content="written", tool_call_id="call_scripted_write"),
        ]
    )

    assert isinstance(result, AIMessage)
    assert result.tool_calls == []


def test_the_reviewer_passes_so_a_run_reaches_its_gate() -> None:
    """A failing reviewer would halt the run before any gate the suite is aiming at."""
    verdict = ScriptedChatModel().with_structured_output(ReviewVerdict).invoke("anything")

    assert isinstance(verdict, ReviewVerdict)
    assert verdict.passed is True
    assert verdict.discrepancies == []


async def test_it_answers_on_the_async_path_the_pipeline_uses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The graph awaits every model call (ADR-0009), so sync-only is not enough.

    Without this the model raises ``NotImplementedError`` the moment a real run
    starts, which is how it first failed.
    """
    monkeypatch.setenv(ENABLE_FLAG, "1")
    model = build_scripted_model()

    result = await model.ainvoke(
        [HumanMessage("Save the result to `campaigns/spring/research.md`.")]
    )

    assert isinstance(result, AIMessage)
    assert result.tool_calls[0]["args"]["path"] == "campaigns/spring/research.md"


async def test_it_can_be_bound_to_tools_the_way_a_specialist_binds_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A specialist binds its tools before invoking, so this must not raise.

    Its absence is what made every run fail at ``stage.start``.
    """
    monkeypatch.setenv(ENABLE_FLAG, "1")
    model = build_scripted_model()

    bound = model.bind_tools([])
    result = await bound.ainvoke([HumanMessage("Save to `campaigns/spring/research.md`.")])

    assert isinstance(result, AIMessage)
    assert result.tool_calls[0]["name"] == "write_file"


@pytest.mark.parametrize("stage", PIPELINE, ids=lambda stage: stage.key)
def test_it_writes_the_deliverable_not_the_goal_it_was_told_to_read(
    stage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every real task prompt names inputs *before* the file to save.

    Picking the first path in the prompt therefore overwrites the campaign goal
    and the stage never produces its deliverable — which is exactly how this
    first failed, against every stage at once. Driven by the real prompts, since
    a simplified one is what hid it.
    """
    monkeypatch.setenv(ENABLE_FLAG, "1")
    slug = "spring"
    task = stage.task.format(
        goal_path=f"campaigns/{slug}/goal.md",
        dna_path="dna.md",
        deliverable_path=f"campaigns/{slug}/{stage.deliverable}",
        prereq_path=f"campaigns/{slug}/{stage.prerequisite or 'goal.md'}",
    )

    result = build_scripted_model().invoke([HumanMessage(task)])

    assert isinstance(result, AIMessage)
    assert result.tool_calls[0]["args"]["path"] == f"campaigns/{slug}/{stage.deliverable}"
