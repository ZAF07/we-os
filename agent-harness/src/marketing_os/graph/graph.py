"""Graph assembly — build the campaign StateGraph from the mandatory pipeline.

The top-level graph is flat and generated from :data:`PIPELINE`: a gate node
followed by, for each stage, an enter/specialist/review trio wired with the QA
revise loop. A single-stage graph reuses the same stage builder for the ``--stage``
workflow. Both compile with a checkpointer so runs are resumable by ``thread_id``.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..adapters.models import get_model
from ..adapters.review import LLMReviewer
from ..adapters.tools import FilesystemSandbox, WebSearchTool, build_tools
from ..agents.loader import AgentSpec, load_agent
from ..agents.specialist import DIRECTOR_BODY, build_specialist
from ..config import Settings
from ..governance import load_governance
from ..governance.pipeline import DIRECTOR, PIPELINE, PIPELINE_BY_KEY, Stage
from ..ports import Reviewer
from .nodes import (
    make_enter_node,
    make_gate_node,
    make_review_node,
    make_specialist_node,
    route_after_enter,
    route_after_review,
)
from .state import CampaignState


def _director_spec() -> AgentSpec:
    """Return the inline specialist definition for the Director-owned stage.

    Returns:
        The :class:`AgentSpec` for the campaign-strategy stage, which has no file
        under ``.claude/agents/`` because the Director owns it directly.
    """
    return AgentSpec(
        name=DIRECTOR,
        description="Marketing Director — campaign strategy, budget, KPIs.",
        tools=["Read", "Grep", "Glob", "Write"],
        body=DIRECTOR_BODY,
    )


def _build_stage_agent(
    settings: Settings,
    stage: Stage,
    model: BaseChatModel,
    governance: str,
    web_backend: WebSearchTool | None,
) -> Runnable:
    """Build the specialist agent for one stage.

    Args:
        settings: The harness settings.
        stage: The pipeline stage to build an agent for.
        model: The chat model the specialist reasons with.
        governance: The governance preamble baked into the system prompt.
        web_backend: The web backend for stages whose agent declares web tools.

    Returns:
        The compiled specialist agent for the stage.
    """
    spec = _director_spec() if stage.agent == DIRECTOR else load_agent(settings, stage.agent)
    sandbox = FilesystemSandbox(settings.root, write_prefixes=["campaigns"])
    tools = build_tools(spec.tools, sandbox=sandbox, web_backend=web_backend)
    return build_specialist(spec, model=model, tools=tools, governance=governance)


def _add_stage(
    builder: StateGraph,
    settings: Settings,
    stage: Stage,
    agent: Runnable,
    reviewer: Reviewer,
    advance_target: str,
) -> str:
    """Add a stage's enter/specialist/review nodes and wire the QA loop.

    Args:
        builder: The graph builder to add nodes and edges to.
        settings: The harness settings.
        stage: The pipeline stage to add.
        agent: The compiled specialist agent for the stage.
        reviewer: The QA reviewer for the stage.
        advance_target: The node (or ``END``) to route to when the stage passes.

    Returns:
        The name of the stage's entry node.
    """
    enter = f"{stage.key}__enter"
    specialist = f"{stage.key}__specialist"
    review = f"{stage.key}__review"
    builder.add_node(enter, make_enter_node(settings, stage))
    builder.add_node(specialist, make_specialist_node(settings, stage, agent))
    builder.add_node(review, make_review_node(settings, stage, reviewer))
    builder.add_conditional_edges(enter, route_after_enter, {"specialist": specialist, "end": END})
    builder.add_edge(specialist, review)
    builder.add_conditional_edges(
        review,
        route_after_review,
        {"revise": specialist, "advance": advance_target, "fail": END},
    )
    return enter


def _route_after_gate(state: CampaignState) -> str:
    """Route out of the gate node.

    Args:
        state: The campaign state after the gate ran.

    Returns:
        ``"end"`` when the gate halted the run, otherwise ``"continue"``.
    """
    return "end" if state.get("halt") else "continue"


def _compile(builder: StateGraph, checkpointer: BaseCheckpointSaver | None) -> CompiledStateGraph:
    """Compile a graph builder with a checkpointer.

    Args:
        builder: The graph builder to compile.
        checkpointer: The checkpointer to use; a :class:`MemorySaver` is used when
            ``None`` so single-process runs are resumable out of the box.

    Returns:
        The compiled graph.
    """
    return builder.compile(checkpointer=checkpointer or MemorySaver())


def build_campaign_graph(
    settings: Settings,
    *,
    model: BaseChatModel | None = None,
    reviewer: Reviewer | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build and compile the full campaign graph from the mandatory pipeline.

    Args:
        settings: The harness settings.
        model: The specialist chat model; built from ``settings`` when ``None``.
        reviewer: The QA reviewer; built from ``settings`` when ``None``.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer; defaults to :class:`MemorySaver`.

    Returns:
        The compiled campaign graph, keyed at runtime by ``thread_id``.
    """
    governance = load_governance(settings)
    model = model or get_model(settings)
    reviewer = reviewer or LLMReviewer(get_model(settings, role="reviewer"), settings)
    builder = StateGraph(CampaignState)
    builder.add_node("gate", make_gate_node(settings))
    builder.add_edge(START, "gate")

    entries: list[str] = []
    for index, stage in enumerate(PIPELINE):
        advance_target = f"{PIPELINE[index + 1].key}__enter" if index + 1 < len(PIPELINE) else END
        agent = _build_stage_agent(settings, stage, model, governance, web_backend)
        entries.append(_add_stage(builder, settings, stage, agent, reviewer, advance_target))

    builder.add_conditional_edges("gate", _route_after_gate, {"continue": entries[0], "end": END})
    return _compile(builder, checkpointer)


def build_single_stage_graph(
    settings: Settings,
    stage_key: str,
    *,
    model: BaseChatModel | None = None,
    reviewer: Reviewer | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build and compile a gate-then-one-stage graph for a single-stage run.

    Args:
        settings: The harness settings.
        stage_key: The key of the single stage to run.
        model: The specialist chat model; built from ``settings`` when ``None``.
        reviewer: The QA reviewer; built from ``settings`` when ``None``.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer; defaults to :class:`MemorySaver`.

    Returns:
        The compiled single-stage graph.

    Raises:
        KeyError: If ``stage_key`` is not a known pipeline stage.
    """
    stage = PIPELINE_BY_KEY[stage_key]
    governance = load_governance(settings)
    model = model or get_model(settings)
    reviewer = reviewer or LLMReviewer(get_model(settings, role="reviewer"), settings)
    builder = StateGraph(CampaignState)
    builder.add_node("gate", make_gate_node(settings))
    builder.add_edge(START, "gate")
    agent = _build_stage_agent(settings, stage, model, governance, web_backend)
    entry = _add_stage(builder, settings, stage, agent, reviewer, END)
    builder.add_conditional_edges("gate", _route_after_gate, {"continue": entry, "end": END})
    return _compile(builder, checkpointer)
