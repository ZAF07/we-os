"""Runner — the application layer that drives the graph and shapes its results.

Both entrypoints (CLI and API) use these helpers so graph selection, error
mapping, and result assembly live in one place. A run is keyed by ``thread_id`` so
it is resumable; single-stage runs use a stage-scoped thread so they do not
collide with the full-campaign thread.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from marketing_os.adapters.tools import WebSearchTool
from marketing_os.config import Settings
from marketing_os.errors import GateError, GuardrailError, PipelineError
from marketing_os.graph.graph import build_campaign_graph, build_single_stage_graph
from marketing_os.graph.state import CampaignState
from marketing_os.schemas import CampaignResult, StageResult, Usage


def thread_id(slug: str, stage: str | None) -> str:
    """Return the checkpoint thread id for a run.

    Args:
        slug: The campaign slug.
        stage: The single stage being run, or ``None`` for the full pipeline.

    Returns:
        ``slug`` for a full run, or ``slug:stage`` for a single-stage run.
    """
    return f"{slug}:{stage}" if stage else slug


def _select_graph(
    settings: Settings,
    stage: str | None,
    *,
    web_backend: WebSearchTool | None,
    checkpointer: BaseCheckpointSaver | None,
) -> Any:
    """Build the campaign or single-stage graph for a run.

    Args:
        settings: The harness settings.
        stage: The single stage to run, or ``None`` for the full pipeline.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer.

    Returns:
        The compiled graph to run.
    """
    if stage:
        return build_single_stage_graph(
            settings, stage, web_backend=web_backend, checkpointer=checkpointer
        )
    return build_campaign_graph(settings, web_backend=web_backend, checkpointer=checkpointer)


def _raise_on_error(state: CampaignState) -> None:
    """Translate a halting state error into the typed exception hierarchy.

    Args:
        state: The final campaign state.

    Raises:
        GateError: If the run halted on the Stage 0 gate.
        PipelineError: If a stage's prerequisite was missing or it never saved.
        GuardrailError: If a deliverable failed QA within the revision budget.
    """
    error = state.get("error")
    if not error:
        return
    kind = error.get("type")
    if kind == "gate":
        issues = [str(issue) for issue in error.get("issues", [])]
        raise GateError("Stage 0 gate failed: " + "; ".join(issues), missing=issues)
    if kind == "pipeline":
        raise PipelineError(
            f"Stage '{error.get('stage')}' cannot start: prerequisite "
            f"'{error.get('prerequisite')}' does not exist."
        )
    if kind == "save":
        raise PipelineError(
            f"Stage '{error.get('stage')}' did not save its deliverable to "
            f"{error.get('deliverable')}."
        )
    if kind == "guardrail":
        raise GuardrailError(
            f"Stage '{error.get('stage')}' failed QA and could not be reconciled.",
            discrepancies=error.get("discrepancies", []),
        )
    raise PipelineError(f"Run halted: {error}")


def _to_result(customer: str, slug: str, state: CampaignState) -> CampaignResult:
    """Assemble a :class:`CampaignResult` from the final graph state.

    Args:
        customer: The customer the campaign ran for.
        slug: The campaign slug.
        state: The final campaign state.

    Returns:
        The structured campaign result.
    """
    stages = [StageResult(**record) for record in state.get("results", [])]
    usage = Usage(**state.get("usage", {}))
    return CampaignResult(customer=customer, slug=slug, stages=stages, usage=usage)


def run_campaign(
    settings: Settings,
    customer: str,
    slug: str,
    *,
    stage: str | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CampaignResult:
    """Run a campaign (or a single stage) to completion in one graph run.

    When ``on_event`` is supplied the run streams and each semantic progress
    event is passed to it; otherwise the run is invoked without streaming.

    Args:
        settings: The harness settings.
        customer: The customer name.
        slug: The campaign slug.
        stage: The single stage to run, or ``None`` for the full pipeline.
        on_event: An optional callback invoked with each progress event.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer.

    Returns:
        The structured campaign result.

    Raises:
        GateError: If the run halted on the Stage 0 gate.
        PipelineError: If a prerequisite was missing or a deliverable never saved.
        GuardrailError: If a deliverable failed QA within the revision budget.
    """
    graph = _select_graph(settings, stage, web_backend=web_backend, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id(slug, stage)}}
    inbound = {"customer": customer, "slug": slug}
    if on_event is None:
        graph.invoke(inbound, config=config)
    else:
        for mode, chunk in graph.stream(inbound, config=config, stream_mode=["custom", "updates"]):
            if mode == "custom":
                on_event(chunk)
    state: CampaignState = graph.get_state(config).values
    _raise_on_error(state)
    return _to_result(customer, slug, state)


async def astream_campaign(
    settings: Settings,
    customer: str,
    slug: str,
    *,
    stage: str | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream a campaign run as semantic progress events.

    Yields each event emitted by the nodes, then a terminal ``campaign.done`` or
    ``error`` event derived from the final state.

    Args:
        settings: The harness settings.
        customer: The customer name.
        slug: The campaign slug.
        stage: The single stage to run, or ``None`` for the full pipeline.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer.

    Yields:
        Event dictionaries with an ``event`` key and event-specific fields.
    """
    graph = _select_graph(settings, stage, web_backend=web_backend, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id(slug, stage)}}
    async for mode, chunk in graph.astream(
        {"customer": customer, "slug": slug},
        config=config,
        stream_mode=["custom", "updates"],
    ):
        if mode == "custom":
            yield chunk
    final = (await graph.aget_state(config)).values
    error = final.get("error")
    if error:
        yield {"event": "error", "error": error}
    else:
        yield {"event": "campaign.done", "results": final.get("results", [])}
