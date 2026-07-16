"""Runner — the application layer that drives the graph and shapes its results.

Both entrypoints (CLI and API) use these helpers so graph selection, error
mapping, and result assembly live in one place. A run is keyed by ``thread_id`` so
it is resumable; single-stage runs use a stage-scoped thread so they do not
collide with the full-campaign thread.
"""

from __future__ import annotations

import asyncio
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
from marketing_os.errors import exception_from_state_error
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
    (``MARKETING_OS_WEB=1``): when web access is enabled a fallback chain is built
    from ``settings.web_backends`` (an ordered list of ``tavily`` / ``google`` /
    ``duckduckgo`` / ``noop``) and owned by the runner (closed when the run ends);
    Tavily is skipped with a warning when its key is unset. When disabled
    the result is ``None`` so ``build_tools`` falls back to :class:`NoopWebSearch`.
    Each backend's Playwright driver is launched lazily on first tool call, so an
    owned-but-unused chain stays cheap.

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
    from marketing_os.adapters.tools import build_web_backend

    chain = build_web_backend(
        settings.web_backends,
        tavily_api_key=settings.tavily_api_key,
        tavily_search_depth=settings.tavily_search_depth,
    )
    return chain, True


def _raise_on_error(state: CampaignState, run_log: str | None) -> None:
    """Raise the typed exception for a halting state error, if the run halted.

    The mapping from the state-error dict to the typed exception (with its
    structured ``detail`` payload) lives in :func:`exception_from_state_error`.

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
    raise exception_from_state_error(error, run_log)


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


def _emit_summary(
    trace: RunTrace | None,
    run_log: str | None,
    *,
    outcome: str,
    error: Any,
    results: list[Any],
    usage: dict[str, int],
) -> None:
    """Write one terminal ``run.summary`` line to the trace and console log.

    Args:
        trace: The open trace, or ``None``.
        run_log: The repo-relative trace path, if any.
        outcome: The terminal outcome, ``"ok"`` or ``"error"``.
        error: The structured error payload, or ``None`` on success.
        results: The per-stage results to record.
        usage: The token usage to record.
    """
    if trace is not None:
        trace.summary(outcome=outcome, error=error, results=results, usage=usage)
    if error is None:
        _LOGGER.info("run.summary outcome=%s run_log=%s", outcome, run_log)
    else:
        _LOGGER.info("run.summary outcome=%s error=%s run_log=%s", outcome, error, run_log)


def _write_summary(trace: RunTrace | None, state: CampaignState, run_log: str | None) -> None:
    """Write the terminal summary line from the final state.

    Args:
        trace: The open trace, or ``None``.
        state: The final campaign state.
        run_log: The repo-relative trace path, if any.
    """
    error = state.get("error")
    _emit_summary(
        trace,
        run_log,
        outcome="error" if error else "ok",
        error=error,
        results=state.get("results", []),
        usage=state.get("usage", {}),
    )


def _write_cancelled_summary(trace: RunTrace | None, run_log: str | None) -> None:
    """Write the terminal ``cancelled`` summary for a run whose task was cancelled.

    Cancellation is the third terminal outcome alongside ``ok`` and ``error``. It
    rides the same issue-01 wrapper: when the run's :class:`asyncio.Task` is
    cancelled (by the cancel endpoint), the escaping :class:`asyncio.CancelledError`
    lands here so the trace still ends with a terminal ``run.summary`` event and a
    later status query resolves to ``cancelled`` rather than ``interrupted``.

    Args:
        trace: The open trace, or ``None``.
        run_log: The repo-relative trace path, if any.
    """
    _emit_summary(
        trace,
        run_log,
        outcome="cancelled",
        error=None,
        results=[],
        usage={},
    )


def _write_error_summary(trace: RunTrace | None, exc: BaseException, run_log: str | None) -> None:
    """Write a terminal error summary for a run killed by an escaping exception.

    Used on the crash path where the graph stream raised an unexpected exception
    (anything outside the :class:`MarketingOSError` hierarchy) before a terminal
    event could be written. The final state is unreliable after such a crash, so
    the outcome is derived from the exception itself rather than from state.

    Args:
        trace: The open trace, or ``None``.
        exc: The exception that escaped the graph stream.
        run_log: The repo-relative trace path, if any.
    """
    _emit_summary(
        trace,
        run_log,
        outcome="error",
        error={"type": "crash", "message": repr(exc)},
        results=[],
        usage={},
    )


async def arun_campaign(
    settings: Settings,
    customer: str,
    slug: str,
    *,
    stage: str | None = None,
    run_id: str | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CampaignResult:
    """Run a campaign (or a single stage) to completion on the async graph path.

    This is the cancellable run path (ADR-0009): the graph is driven with
    ``astream`` so every specialist and review LLM call is an awaited coroutine.
    Launched as an :class:`asyncio.Task`, the run can be cancelled such that the
    ``CancelledError`` aborts the in-flight LLM request; the escaping cancellation
    still writes a terminal ``run.summary outcome=cancelled`` before propagating.
    The run always streams internally so every event is logged to the console and
    appended to the run's JSONL trace, regardless of whether ``on_event`` is given.

    Args:
        settings: The harness settings.
        customer: The customer name.
        slug: The campaign slug.
        stage: The single stage to run, or ``None`` for the full pipeline.
        run_id: The id used as the trace filename; a fresh id is generated when
            ``None``. The API supplies one up front so it can register and return
            the run before the pipeline starts.
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
    trace = _open_trace(settings, slug, run_id or new_run_id())
    run_log = _rel_log(settings, trace)
    _LOGGER.info(
        "run.start customer=%s slug=%s stage=%s run_log=%s", customer, slug, stage, run_log
    )
    try:
        async for mode, chunk in graph.astream(
            inbound, config=config, stream_mode=["custom", "updates"]
        ):
            if mode != "custom":
                continue
            if trace is not None:
                trace.event(chunk)
            if on_event is not None:
                on_event(chunk)
        state: CampaignState = (await graph.aget_state(config)).values
        _write_summary(trace, state, run_log)
    except asyncio.CancelledError:
        _write_cancelled_summary(trace, run_log)
        raise
    except Exception as exc:
        _write_error_summary(trace, exc, run_log)
        raise
    finally:
        if trace is not None:
            trace.close()
        if owns_backend and backend is not None:
            backend.close()
    _raise_on_error(state, run_log)
    return _to_result(customer, slug, state, run_log)


def run_campaign(
    settings: Settings,
    customer: str,
    slug: str,
    *,
    stage: str | None = None,
    run_id: str | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CampaignResult:
    """Run a campaign (or a single stage) to completion, blocking until done.

    A synchronous convenience wrapper for the CLI and other sync callers: it drives
    :func:`arun_campaign` on a fresh event loop via :func:`asyncio.run`. Callers
    that need to cancel a run (the API) must await :func:`arun_campaign` directly so
    the run is an :class:`asyncio.Task` on their loop.

    Args:
        settings: The harness settings.
        customer: The customer name.
        slug: The campaign slug.
        stage: The single stage to run, or ``None`` for the full pipeline.
        run_id: The id used as the trace filename; a fresh id is generated when
            ``None``.
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
    return asyncio.run(
        arun_campaign(
            settings,
            customer,
            slug,
            stage=stage,
            run_id=run_id,
            on_event=on_event,
            web_backend=web_backend,
            checkpointer=checkpointer,
        )
    )


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
    except Exception as exc:
        _write_error_summary(trace, exc, run_log)
        raise
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
