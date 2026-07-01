"""Graph integration tests: gate, specialist, QA loop, save-retry, and prereq halt.

These drive the compiled graph with a scripted chat model and a fake reviewer, so
no network is used. The model writes whichever deliverable the seeded task names.
"""

from __future__ import annotations

import re

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from conftest import FakeReviewer, ProgrammableChatModel, write_call
from marketing_os.config import Settings
from marketing_os.graph.graph import build_campaign_graph, build_single_stage_graph
from marketing_os.schemas import Discrepancy, ReviewVerdict

_PASS = ReviewVerdict(passed=True, summary="ok")
_FAIL = ReviewVerdict(
    passed=False,
    summary="needs work",
    discrepancies=[Discrepancy(rubric_point="x", problem="p", fix="f")],
)


def _deliverable_from(messages: list[BaseMessage]) -> str:
    """Extract the campaigns/*.md deliverable path named in the seeded task.

    Args:
        messages: The conversation so far.

    Returns:
        The first ``campaigns/<slug>/<name>.md`` path found.
    """
    text = "\n".join(str(m.content) for m in messages)
    matches = re.findall(r"campaigns/[\w-]+/[\w-]+\.md", text)
    assert matches, "no deliverable path in task"
    return matches[-1]


def _writing_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write the named deliverable, then stop once the tool has run.

    Args:
        messages: The conversation so far.
        index: The model-call index (unused).

    Returns:
        A write-tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    path = _deliverable_from(messages)
    return write_call(path, f"# Deliverable\n\nContent for {path}.")


def _refusing_then_writing_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Skip saving until told to, to exercise the save-retry path.

    Args:
        messages: The conversation so far.
        index: The model-call index (unused).

    Returns:
        A completion that does not save on the first pass, then a write once the
        save-retry instruction appears.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    text = "\n".join(str(m.content) for m in messages)
    if "have not saved" in text:
        return write_call(_deliverable_from(messages), "# Deliverable\n\nSaved late.")
    return AIMessage(content="All done (but I forgot to save).")


def _config(thread: str) -> dict:
    """Build an invoke config with a thread id and a generous recursion limit.

    Args:
        thread: The checkpoint thread id.

    Returns:
        The runnable config.
    """
    return {"configurable": {"thread_id": thread}, "recursion_limit": 50}


def _write_specs(settings: Settings) -> None:
    """Write the remaining specialist specs so a full pipeline run can build.

    Args:
        settings: The harness settings locating the agents directory.
    """
    specs = {
        "brand-strategy": "You are the Brand Strategy Agent.",
        "creative-director": "You are the Creative Director Agent.",
        "creative-asset-prompt": "You are the Creative Asset Prompt Agent.",
        "performance-marketing": "You are the Performance Marketing Agent.",
    }
    for name, body in specs.items():
        path = settings.agents_dir / f"{name}.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {name}\ntools: Read, Grep, Glob, Write\n---\n{body}",
            encoding="utf-8",
        )


def test_single_stage_happy_path(settings: Settings) -> None:
    reviewer = FakeReviewer([_PASS])
    graph = build_single_stage_graph(
        settings,
        "research",
        model=ProgrammableChatModel(handler=_writing_handler),
        reviewer=reviewer,
    )
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t1"))
    assert (settings.campaigns_dir / "acme" / "research.md").is_file()
    assert state["error"] is None
    assert state["results"][0]["approved"] is True
    assert state["results"][0]["qa_iterations"] == 0
    assert len(reviewer.calls) == 1


def test_save_retry_forces_a_write(settings: Settings) -> None:
    reviewer = FakeReviewer([_PASS])
    model = ProgrammableChatModel(handler=_refusing_then_writing_handler)
    graph = build_single_stage_graph(settings, "research", model=model, reviewer=reviewer)
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t2"))
    assert (settings.campaigns_dir / "acme" / "research.md").is_file()
    assert state["error"] is None
    assert state["results"][0]["save_retries"] == 1


def test_qa_revise_loop_until_pass(settings: Settings) -> None:
    reviewer = FakeReviewer([_FAIL, _PASS])
    graph = build_single_stage_graph(
        settings,
        "research",
        model=ProgrammableChatModel(handler=_writing_handler),
        reviewer=reviewer,
    )
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t3"))
    assert state["error"] is None
    assert state["results"][0]["approved"] is True
    assert state["results"][0]["qa_iterations"] == 1
    assert len(reviewer.calls) == 2


def test_qa_budget_exhausted_fails(settings: Settings) -> None:
    reviewer = FakeReviewer([_FAIL])
    settings.max_qa_iterations = 1
    graph = build_single_stage_graph(
        settings,
        "research",
        model=ProgrammableChatModel(handler=_writing_handler),
        reviewer=reviewer,
    )
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t4"))
    assert state["error"]["type"] == "guardrail"
    assert state["results"][0]["approved"] is False


def test_gate_halts_on_placeholder_dna(settings: Settings) -> None:
    dna = settings.customers_dir / "acme" / "dna.md"
    dna.write_text(
        "# Customer DNA — Acme\n\n## Business\n- **Business name:** <name>\n",
        encoding="utf-8",
    )
    reviewer = FakeReviewer([_PASS])
    graph = build_single_stage_graph(
        settings,
        "research",
        model=ProgrammableChatModel(handler=_writing_handler),
        reviewer=reviewer,
    )
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t5"))
    assert state["error"]["type"] == "gate"
    assert not (settings.campaigns_dir / "acme" / "research.md").is_file()


def test_prerequisite_halts_when_upstream_missing(settings: Settings) -> None:
    _write_specs(settings)
    reviewer = FakeReviewer([_PASS])
    graph = build_single_stage_graph(
        settings,
        "brand-strategy",
        model=ProgrammableChatModel(handler=_writing_handler),
        reviewer=reviewer,
    )
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t6"))
    assert state["error"]["type"] == "pipeline"
    assert state["error"]["prerequisite"] == "research.md"


def test_full_pipeline_advances_through_every_stage(settings: Settings) -> None:
    _write_specs(settings)
    reviewer = FakeReviewer([_PASS])
    graph = build_campaign_graph(
        settings, model=ProgrammableChatModel(handler=_writing_handler), reviewer=reviewer
    )
    state = graph.invoke({"customer": "acme", "slug": "acme"}, config=_config("t7"))
    assert state["error"] is None
    stages = [record["stage"] for record in state["results"]]
    assert stages == [
        "research",
        "brand-strategy",
        "campaign-strategy",
        "creative-brief",
        "asset-prompts",
        "performance-plan",
    ]
    for name in ("research.md", "brand-strategy.md", "performance-plan.md"):
        assert (settings.campaigns_dir / "acme" / name).is_file()
