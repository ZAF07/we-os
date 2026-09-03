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

from marketing_os.adapters.deliverables import FilesystemDeliverableStore
from marketing_os.adapters.documents import FilesystemDocumentStore
from marketing_os.adapters.models import get_model
from marketing_os.adapters.review import LLMReviewer
from marketing_os.adapters.tools import FilesystemSandbox, WebSearchTool, build_tools
from marketing_os.agents.spec_source import SpecSource
from marketing_os.agents.specialist import build_specialist
from marketing_os.config import Role, Settings
from marketing_os.governance import load_governance
from marketing_os.governance.pipeline import (
    HUMAN,
    PIPELINE,
    PIPELINE_BY_KEY,
    Stage,
    apply_approval_policies,
)
from marketing_os.graph.nodes import (
    make_approval_node,
    make_enter_node,
    make_gate_node,
    make_review_node,
    make_specialist_node,
    route_after_approval,
    route_after_enter,
    route_after_review,
)
from marketing_os.graph.state import CampaignState
from marketing_os.ports import DeliverableStore, DocumentStore, Reviewer


def _build_stage_agent(
    settings: Settings,
    stage: Stage,
    model: BaseChatModel,
    governance: str,
    web_backend: WebSearchTool | None,
    spec_source: SpecSource,
    store: DocumentStore,
) -> Runnable:
    """Build the specialist agent for one stage.

    Args:
        settings: The harness settings.
        stage: The pipeline stage to build an agent for.
        model: The chat model the specialist reasons with.
        governance: The governance preamble baked into the system prompt.
        web_backend: The web backend for stages whose agent declares web tools.
        spec_source: The source resolving the stage's specialist definition.
        store: The document store deliverable writes resolve through.

    Returns:
        The compiled specialist agent for the stage.
    """
    spec = spec_source.spec_for(stage.agent)
    sandbox = FilesystemSandbox(settings.root)
    tools = build_tools(spec.tools, sandbox=sandbox, web_backend=web_backend, document_store=store)
    return build_specialist(spec, model=model, tools=tools, governance=governance)


def _add_stage(
    builder: StateGraph,
    settings: Settings,
    stage: Stage,
    agent: Runnable,
    reviewer: Reviewer,
    store: DocumentStore,
    deliverables: DeliverableStore,
    advance_target: str,
) -> str:
    """Add a stage's nodes and wire the QA loop and, when gated, its Approval Gate.

    A ``human``-policy stage gets a fourth node between review and the next
    stage. Everything downstream of that node is unreachable until a person
    decides, which is how "creative cannot be produced before a human-approved
    strategy exists" becomes a property of the graph rather than a convention
    (ADR-0015). Refusing at the gate routes back to the stage's **entry** node,
    not its specialist, so the re-run starts a clean attempt seeded with the
    feedback rather than appending to the transcript the person rejected.

    Args:
        builder: The graph builder to add nodes and edges to.
        settings: The harness settings.
        stage: The pipeline stage to add.
        agent: The compiled specialist agent for the stage.
        reviewer: The QA reviewer for the stage.
        store: The document store the stage's deliverables resolve through.
        deliverables: The store each passing deliverable is versioned into.
        advance_target: The node (or ``END``) to route to when the stage passes.

    Returns:
        The name of the stage's entry node.
    """
    enter = f"{stage.key}__enter"
    specialist = f"{stage.key}__specialist"
    review = f"{stage.key}__review"
    builder.add_node(enter, make_enter_node(stage, store))
    builder.add_node(specialist, make_specialist_node(settings, stage, agent))
    builder.add_node(review, make_review_node(settings, stage, reviewer, store, deliverables))
    builder.add_conditional_edges(enter, route_after_enter, {"specialist": specialist, "end": END})
    builder.add_edge(specialist, review)

    passed_target = advance_target
    if stage.approval_policy == HUMAN:
        approval = f"{stage.key}__approval"
        builder.add_node(approval, make_approval_node(settings, stage, deliverables))
        builder.add_conditional_edges(
            approval,
            route_after_approval,
            {"advance": advance_target, "revise": enter, "fail": END},
        )
        passed_target = approval

    builder.add_conditional_edges(
        review,
        route_after_review,
        {
            "revise": specialist,
            "advance": passed_target,
            "approval": passed_target,
            "fail": END,
        },
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
    document_store: DocumentStore | None = None,
    deliverable_store: DeliverableStore | None = None,
) -> CompiledStateGraph:
    """Build and compile the full campaign graph from the mandatory pipeline.

    The stages' approval policies come from ``settings`` before the graph is
    wired, so which stages halt at an Approval Gate is a configuration change
    rather than a code change (ADR-0015).

    Args:
        settings: The harness settings.
        model: The specialist chat model; built from ``settings`` when ``None``.
        reviewer: The QA reviewer; built from ``settings`` when ``None``.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer; defaults to :class:`MemorySaver`.
        document_store: The store tenant documents resolve through; defaults to
            the filesystem adapter rooted at the repo root.
        deliverable_store: The store deliverable versions are appended to;
            defaults to the filesystem adapter rooted at the repo root.

    Returns:
        The compiled campaign graph, keyed at runtime by ``thread_id``.
    """
    governance = load_governance(settings)
    model = model or get_model(settings)
    reviewer = reviewer or LLMReviewer(
        get_model(settings, role=Role.REVIEWER, thinking=settings.reviewer_thinking), settings
    )
    store = document_store or FilesystemDocumentStore(settings.root)
    versions = deliverable_store or FilesystemDeliverableStore(settings.root)
    spec_source = SpecSource(settings)
    builder = StateGraph(CampaignState)
    builder.add_node("gate", make_gate_node(settings, store))
    builder.add_edge(START, "gate")

    stages = apply_approval_policies(PIPELINE, settings.human_gate_stages)
    entries: list[str] = []
    for index, stage in enumerate(stages):
        advance_target = f"{stages[index + 1].key}__enter" if index + 1 < len(stages) else END
        agent = _build_stage_agent(
            settings, stage, model, governance, web_backend, spec_source, store
        )
        entries.append(
            _add_stage(builder, settings, stage, agent, reviewer, store, versions, advance_target)
        )

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
    document_store: DocumentStore | None = None,
    deliverable_store: DeliverableStore | None = None,
) -> CompiledStateGraph:
    """Build and compile a gate-then-one-stage graph for a single-stage run.

    Args:
        settings: The harness settings.
        stage_key: The key of the single stage to run.
        model: The specialist chat model; built from ``settings`` when ``None``.
        reviewer: The QA reviewer; built from ``settings`` when ``None``.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer; defaults to :class:`MemorySaver`.
        document_store: The store tenant documents resolve through; defaults to
            the filesystem adapter rooted at the repo root.
        deliverable_store: The store deliverable versions are appended to;
            defaults to the filesystem adapter rooted at the repo root.

    Returns:
        The compiled single-stage graph.

    Raises:
        KeyError: If ``stage_key`` is not a known pipeline stage.
    """
    stage = _policied_stage(settings, stage_key)
    governance = load_governance(settings)
    model = model or get_model(settings)
    reviewer = reviewer or LLMReviewer(
        get_model(settings, role=Role.REVIEWER, thinking=settings.reviewer_thinking), settings
    )
    store = document_store or FilesystemDocumentStore(settings.root)
    versions = deliverable_store or FilesystemDeliverableStore(settings.root)
    spec_source = SpecSource(settings)
    builder = StateGraph(CampaignState)
    builder.add_node("gate", make_gate_node(settings, store))
    builder.add_edge(START, "gate")
    agent = _build_stage_agent(settings, stage, model, governance, web_backend, spec_source, store)
    entry = _add_stage(builder, settings, stage, agent, reviewer, store, versions, END)
    builder.add_conditional_edges("gate", _route_after_gate, {"continue": entry, "end": END})
    return _compile(builder, checkpointer)


def _policied_stage(settings: Settings, stage_key: str) -> Stage:
    """Return one pipeline stage carrying its configured approval policy.

    Args:
        settings: The harness settings holding the approval configuration.
        stage_key: The stage to resolve.

    Returns:
        The stage with its policy applied.

    Raises:
        KeyError: If ``stage_key`` is not a known pipeline stage.
    """
    stage = PIPELINE_BY_KEY[stage_key]
    return apply_approval_policies([stage], settings.human_gate_stages)[0]
