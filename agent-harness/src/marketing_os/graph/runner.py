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

from marketing_os.adapters.observability import (
    RunTrace,
    get_logger,
    new_run_id,
    run_config,
)
from marketing_os.adapters.tools import WebSearchTool
from marketing_os.config import Settings
from marketing_os.errors import GateError, GuardrailError, MarketingOSError, PipelineError
from marketing_os.graph.graph import build_campaign_graph, build_single_stage_graph
from marketing_os.graph.state import CampaignState
from marketing_os.schemas import CampaignResult, StageResult, Usage

_LOGGER = get_logger("marketing_os.runner")


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


def _resolve_web_backend(
    settings: Settings, web_backend: WebSearchTool | None
) -> tuple[WebSearchTool | None, bool]:
    """Resolve the web backend for a run and whether the runner owns its lifecycle.

    A caller-supplied ``web_backend`` is used as-is and never closed by the runner
    (the caller owns it). Otherwise the backend is gated on ``settings.enable_web``
    (``MARKETING_OS_WEB=1``): when web access is enabled a
    :class:`PlaywrightWebSearch` is created and owned by the runner (closed when the
    run ends); when disabled the result is ``None`` so ``build_tools`` falls back to
    :class:`NoopWebSearch`. The Playwright driver is launched lazily on first tool
    call, so an owned-but-unused backend stays cheap.

    Args:
        settings: The harness settings.
        web_backend: A caller-supplied backend, or ``None`` to resolve the default.

    Returns:
        A ``(backend, owns_backend)`` pair. ``owns_backend`` is ``True`` only when
        the runner created the backend and is responsible for closing it.
    """
    if web_backend is not None:
        return web_backend, False
    if not settings.enable_web:
        return None, False
    from marketing_os.adapters.tools.websearch_playwright import PlaywrightWebSearch

    return PlaywrightWebSearch(), True


def _raise_on_error(state: CampaignState, run_log: str | None) -> None:
    """Translate a halting state error into the typed exception hierarchy.

    The raised exception carries a structured ``detail`` dict (and the ``run_log``
    path) so the API can return the failure reason to the client.

    Args:
        state: The final campaign state.
        run_log: The repo-relative path of the run's JSONL trace, if any.

    Raises:
        GateError: If the run halted on the Stage 0 gate.
        PipelineError: If a stage's prerequisite was missing or it never saved.
        GuardrailError: If a deliverable failed QA within the revision budget.
    """
    error = state.get("error")
    if not error:
        return
    kind = error.get("type")
    stage = error.get("stage")
    if kind == "gate":
        issues = [str(issue) for issue in error.get("issues", [])]
        message = "Stage 0 gate failed: " + "; ".join(issues)
        exc: MarketingOSError = GateError(message, missing=issues)
        detail: dict[str, Any] = {"message": message, "issues": issues}
    elif kind == "pipeline":
        message = (
            f"Stage '{stage}' cannot start: prerequisite "
            f"'{error.get('prerequisite')}' does not exist."
        )
        exc = PipelineError(message)
        detail = {"message": message, "prerequisite": error.get("prerequisite")}
    elif kind == "save":
        message = f"Stage '{stage}' did not save its deliverable to {error.get('deliverable')}."
        exc = PipelineError(message)
        detail = {"message": message, "deliverable": error.get("deliverable")}
    elif kind == "guardrail":
        message = f"Stage '{stage}' failed QA and could not be reconciled."
        exc = GuardrailError(message, discrepancies=error.get("discrepancies", []))
        detail = {
            "message": message,
            "summary": error.get("summary"),
            "discrepancies": error.get("discrepancies", []),
        }
    else:
        message = f"Run halted: {error}"
        exc = PipelineError(message)
        detail = {"message": message}
    detail.update({"type": kind, "stage": stage, "run_log": run_log})
    exc.detail = detail
    exc.run_log = run_log
    raise exc


def _to_result(
    customer: str, slug: str, state: CampaignState, run_log: str | None
) -> CampaignResult:
    """Assemble a :class:`CampaignResult` from the final graph state.

    Args:
        customer: The customer the campaign ran for.
        slug: The campaign slug.
        state: The final campaign state.
        run_log: The repo-relative path of the run's JSONL trace, if any.

    Returns:
        The structured campaign result.
    """
    stages = [StageResult(**record) for record in state.get("results", [])]
    usage = Usage(**state.get("usage", {}))
    return CampaignResult(customer=customer, slug=slug, stages=stages, usage=usage, run_log=run_log)


def _open_trace(settings: Settings, slug: str, run_id: str) -> RunTrace | None:
    """Open a per-run JSONL trace under ``logs/`` when run logging is enabled.

    Args:
        settings: The harness settings.
        slug: The campaign slug.
        run_id: The unique run id used as the trace filename.

    Returns:
        An open :class:`RunTrace`, or ``None`` when run logging is disabled.
    """
    if not settings.run_logs:
        return None
    return RunTrace(settings.logs_dir / slug / f"{run_id}.jsonl")


def _rel_log(settings: Settings, trace: RunTrace | None) -> str | None:
    """Return the trace path relative to the repo root, for display.

    Args:
        settings: The harness settings.
        trace: The open trace, or ``None``.

    Returns:
        The repo-relative trace path, or ``None`` when there is no trace.
    """
    if trace is None:
        return None
    return str(trace.path.relative_to(settings.root))


def _config(customer: str, slug: str, stage: str | None) -> dict[str, Any]:
    """Build the LangGraph config for a run, including LangSmith trace metadata.

    Args:
        customer: The customer name.
        slug: The campaign slug.
        stage: The single stage, or ``None`` for the full pipeline.

    Returns:
        The invocation config.
    """
    scope = stage or "full-pipeline"
    return run_config(
        thread_id(slug, stage),
        run_name=f"campaign:{slug}:{scope}",
        metadata={"customer": customer, "slug": slug, "stage": stage},
        tags=["marketing-os", scope],
    )


def _write_summary(trace: RunTrace | None, state: CampaignState, run_log: str | None) -> None:
    """Write the terminal summary line to the trace and log the outcome.

    Args:
        trace: The open trace, or ``None``.
        state: The final campaign state.
        run_log: The repo-relative trace path, if any.
    """
    error = state.get("error")
    outcome = "error" if error else "ok"
    if trace is not None:
        trace.summary(
            outcome=outcome,
            error=error,
            results=state.get("results", []),
            usage=state.get("usage", {}),
        )
    _LOGGER.info("run.summary outcome=%s run_log=%s", outcome, run_log)


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

    The run always streams internally so every event is logged to the console and
    appended to the run's JSONL trace, regardless of whether ``on_event`` is given.

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
    backend, owns_backend = _resolve_web_backend(settings, web_backend)
    graph = _select_graph(settings, stage, web_backend=backend, checkpointer=checkpointer)
    config = _config(customer, slug, stage)
    inbound = {"customer": customer, "slug": slug}
    run_id = new_run_id()
    trace = _open_trace(settings, slug, run_id)
    run_log = _rel_log(settings, trace)
    _LOGGER.info(
        "run.start customer=%s slug=%s stage=%s run_log=%s", customer, slug, stage, run_log
    )
    try:
        for mode, chunk in graph.stream(inbound, config=config, stream_mode=["custom", "updates"]):
            if mode != "custom":
                continue
            if trace is not None:
                trace.event(chunk)
            if on_event is not None:
                on_event(chunk)
        state: CampaignState = graph.get_state(config).values
        _write_summary(trace, state, run_log)
    finally:
        if trace is not None:
            trace.close()
        if owns_backend and backend is not None:
            backend.close()
    _raise_on_error(state, run_log)
    return _to_result(customer, slug, state, run_log)


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
    ``error`` event derived from the final state. Every event is also appended to
    the run's JSONL trace.

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
    backend, owns_backend = _resolve_web_backend(settings, web_backend)
    graph = _select_graph(settings, stage, web_backend=backend, checkpointer=checkpointer)
    config = _config(customer, slug, stage)
    run_id = new_run_id()
    trace = _open_trace(settings, slug, run_id)
    run_log = _rel_log(settings, trace)
    _LOGGER.info(
        "run.start customer=%s slug=%s stage=%s run_log=%s", customer, slug, stage, run_log
    )
    try:
        async for mode, chunk in graph.astream(
            {"customer": customer, "slug": slug},
            config=config,
            stream_mode=["custom", "updates"],
        ):
            if mode != "custom":
                continue
            if trace is not None:
                trace.event(chunk)
            yield chunk
        final = (await graph.aget_state(config)).values
        _write_summary(trace, final, run_log)
    finally:
        if trace is not None:
            trace.close()
        if owns_backend and backend is not None:
            backend.close()
    error = final.get("error")
    if error:
        yield {"event": "error", "error": error, "run_log": run_log}
    else:
        yield {"event": "campaign.done", "results": final.get("results", []), "run_log": run_log}
