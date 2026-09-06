"""Runner — the application layer that drives the graph and shapes its results.

The API entrypoint uses these helpers so graph selection, error mapping, and
result assembly live in one place. A run is keyed by ``thread_id``
(see :mod:`marketing_os.graph.checkpoints`) so it is resumable; single-stage runs
use a stage-scoped thread so they do not collide with the full-campaign thread,
and every thread is tenant-scoped so two businesses running the same slug cannot
share checkpointed state.

``INTERRUPT_CHANNEL`` is the channel LangGraph records a pending ``interrupt()``
under in a checkpoint's writes, and is how a halted run's Approval Gate is found
after a restart. LangGraph exports the name only from a module it asks callers
not to import, so it is spelled here instead.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command

from marketing_os.adapters.observability import (
    RunTrace,
    get_logger,
    new_run_id,
    run_config,
)
from marketing_os.adapters.runs import AWAITING_APPROVAL
from marketing_os.adapters.tools import WebSearchTool
from marketing_os.config import Settings
from marketing_os.errors import exception_from_state_error
from marketing_os.graph.checkpoints import thread_id
from marketing_os.graph.graph import build_campaign_graph, build_single_stage_graph
from marketing_os.graph.state import CampaignState
from marketing_os.ports import DeliverableStore, DocumentStore, UsageLedger
from marketing_os.questionnaire import SEED_QUESTIONNAIRE
from marketing_os.schemas import CampaignResult, Questionnaire, StageResult, Usage

_LOGGER = get_logger("marketing_os.runner")

INTERRUPT_CHANNEL = "__interrupt__"


def _select_graph(
    settings: Settings,
    stage: str | None,
    *,
    web_backend: WebSearchTool | None,
    checkpointer: BaseCheckpointSaver | None,
    document_store: DocumentStore | None,
    deliverable_store: DeliverableStore | None = None,
    usage_ledger: UsageLedger | None = None,
    questionnaire: Questionnaire,
) -> Any:
    """Build the campaign or single-stage graph for a run.

    Args:
        settings: The harness settings.
        stage: The single stage to run, or ``None`` for the full pipeline.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer.
        document_store: The store tenant documents resolve through, or ``None``
            for the filesystem default.
        deliverable_store: The store deliverable versions are appended to, or
            ``None`` for the filesystem default.
        usage_ledger: The Usage Ledger every model call is checked against and
            charged to, or ``None`` to run uncharged.
        questionnaire: The published question set the Stage 0 gate enforces.

    Returns:
        The compiled graph to run.
    """
    if stage:
        return build_single_stage_graph(
            settings,
            stage,
            web_backend=web_backend,
            checkpointer=checkpointer,
            document_store=document_store,
            deliverable_store=deliverable_store,
            usage_ledger=usage_ledger,
            questionnaire=questionnaire,
        )
    return build_campaign_graph(
        settings,
        web_backend=web_backend,
        checkpointer=checkpointer,
        document_store=document_store,
        deliverable_store=deliverable_store,
        usage_ledger=usage_ledger,
        questionnaire=questionnaire,
    )


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
    tenant: str,
    slug: str,
    state: CampaignState,
    run_log: str | None,
    awaiting: str | None = None,
) -> CampaignResult:
    """Assemble a :class:`CampaignResult` from the final graph state.

    Args:
        tenant: The tenant the campaign ran for.
        slug: The campaign slug.
        state: The final campaign state.
        run_log: The repo-relative path of the run's JSONL trace, if any.
        awaiting: The stage halted at an Approval Gate, if the run stopped there.

    Returns:
        The structured campaign result.
    """
    stages = [StageResult(**record) for record in state.get("results", [])]
    usage = Usage(**state.get("usage", {}))
    return CampaignResult(
        tenant=tenant,
        slug=slug,
        stages=stages,
        usage=usage,
        run_log=run_log,
        awaiting_approval_stage=awaiting,
    )


def _open_trace(settings: Settings, tenant: str, slug: str, run_id: str) -> RunTrace | None:
    """Open a per-run JSONL trace under ``logs/<tenant>/`` when run logging is enabled.

    Args:
        settings: The harness settings.
        tenant: The tenant the run belongs to; traces are partitioned by it so a
            run id is only findable by the business that owns it.
        slug: The campaign slug.
        run_id: The unique run id used as the trace filename.

    Returns:
        An open :class:`RunTrace`, or ``None`` when run logging is disabled.
    """
    if not settings.run_logs:
        return None
    return RunTrace(settings.tenant_logs_dir(tenant) / slug / f"{run_id}.jsonl")


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


def _config(tenant: str, slug: str, stage: str | None) -> dict[str, Any]:
    """Build the LangGraph config for a run, including LangSmith trace metadata.

    Args:
        tenant: The tenant name.
        slug: The campaign slug.
        stage: The single stage, or ``None`` for the full pipeline.

    Returns:
        The invocation config.
    """
    scope = stage or "full-pipeline"
    return run_config(
        thread_id(tenant, slug, stage),
        run_name=f"campaign:{slug}:{scope}",
        metadata={"tenant": tenant, "slug": slug, "stage": stage},
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
    **extra: Any,
) -> None:
    """Write one terminal ``run.summary`` line to the trace and console log.

    Args:
        trace: The open trace, or ``None``.
        run_log: The repo-relative trace path, if any.
        outcome: The terminal outcome — ``"ok"``, ``"error"``, ``"cancelled"``,
            or ``"awaiting_approval"`` when a person is holding the run.
        error: The structured error payload, or ``None`` on success.
        results: The per-stage results to record.
        usage: The token usage to record.
        **extra: Additional fields to record on the summary, such as the stage
            an ``awaiting_approval`` run is waiting at.
    """
    if trace is not None:
        trace.summary(outcome=outcome, error=error, results=results, usage=usage, **extra)
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


def _gated_stage(pending: Any) -> str | None:
    """Return the stage named by the first Approval Gate interrupt in a sequence.

    The one place a pending ``interrupt()`` is read, so the snapshot path and the
    checkpoint path cannot come to different answers about which stage is
    waiting.

    Args:
        pending: The pending interrupts to inspect.

    Returns:
        The waiting stage key, or ``None`` when none of them names a stage.
    """
    for interrupted in pending or ():
        payload = getattr(interrupted, "value", None)
        if isinstance(payload, dict) and payload.get("stage"):
            return str(payload["stage"])
    return None


def _awaiting_stage(snapshot: Any) -> str | None:
    """Return the stage a graph snapshot is halted at an Approval Gate for.

    LangGraph records a pending ``interrupt()`` on the snapshot's tasks. Reading
    it from the snapshot rather than from the stream is what makes the answer the
    same whether the run just halted or was reloaded from a checkpoint after a
    restart — which is the whole point of a durable gate (ADR-0015).

    Args:
        snapshot: The graph state snapshot to inspect.

    Returns:
        The waiting stage key, or ``None`` when nothing is waiting on a person.
    """
    for task in getattr(snapshot, "tasks", ()) or ():
        waiting = _gated_stage(getattr(task, "interrupts", ()))
        if waiting is not None:
            return waiting
    return None


def _write_awaiting_summary(trace: RunTrace | None, stage_key: str, run_log: str | None) -> None:
    """Write the terminal ``awaiting_approval`` summary for a gated run.

    A run halted at an Approval Gate has stopped executing, so its trace needs a
    terminal event exactly as a finished one does — but the outcome says the run
    is waiting on a person, not that it is done (ADR-0017).

    Args:
        trace: The open trace, or ``None``.
        stage_key: The stage waiting for approval.
        run_log: The repo-relative trace path, if any.
    """
    _emit_summary(
        trace,
        run_log,
        outcome=AWAITING_APPROVAL,
        error=None,
        results=[],
        usage={},
        stage=stage_key,
    )


async def _drive(
    graph: Any,
    inbound: Any,
    config: dict[str, Any],
    trace: RunTrace | None,
    on_event: Callable[[dict[str, Any]], None] | None,
) -> tuple[CampaignState, str | None]:
    """Stream a graph to a halt and report where it stopped.

    Args:
        graph: The compiled graph to drive.
        inbound: The initial state, or a ``Command`` resuming an interrupt.
        config: The invocation config carrying the checkpoint thread id.
        trace: The open trace events are appended to, or ``None``.
        on_event: An optional callback invoked with each progress event.

    Returns:
        The final state and the stage waiting at an Approval Gate, if any.
    """
    stream = graph.astream(inbound, config=config, stream_mode=["custom", "updates"])
    async for mode, chunk in stream:
        if mode != "custom":
            continue
        if trace is not None:
            trace.event(chunk)
        if on_event is not None:
            on_event(chunk)
    snapshot = await graph.aget_state(config)
    return snapshot.values, _awaiting_stage(snapshot)


def _initial_state(tenant: str, slug: str, feedback: str | None) -> dict[str, Any]:
    """Build the state a fresh run starts from.

    A re-opened stage carries the owner's feedback in on ``human_feedback``, the
    same key an Approval Gate refusal sets, so one seeding path serves both:
    "you approved this and have changed your mind" reaches the specialist as
    "the owner sent this back", with the previous deliverable to revise.

    Args:
        tenant: The tenant the campaign runs for.
        slug: The campaign slug.
        feedback: What the owner wants changed, when re-opening a stage.

    Returns:
        The initial campaign state.
    """
    state: dict[str, Any] = {"tenant": tenant, "slug": slug}
    if feedback:
        state["human_feedback"] = feedback
    return state


async def awaiting_approval_stage(
    tenant: str,
    slug: str,
    *,
    stage: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> str | None:
    """Return the stage a campaign's checkpointed run is halted at, if any.

    Read from the checkpoint rather than from memory or from the trace, so the
    answer survives a restart: a halted run's gate is exactly where its persisted
    state says it is, whichever process asks (ADR-0015). Only the saved state is
    needed, so this asks the checkpointer directly rather than compiling the
    pipeline to get a snapshot.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.
        stage: The single stage the run targeted, or ``None`` for a full run.
        checkpointer: The checkpointer holding the run's state.

    Returns:
        The waiting stage key, or ``None`` when nothing is waiting on a person.
    """
    if checkpointer is None:
        return None
    thread = {"configurable": {"thread_id": thread_id(tenant, slug, stage)}}
    saved = await checkpointer.aget_tuple(cast("RunnableConfig", thread))
    if saved is None:
        return None
    writes = list(saved.pending_writes or ())
    for _, channel, value in writes:
        if channel != INTERRUPT_CHANNEL:
            continue
        waiting = _gated_stage(value if isinstance(value, list) else [value])
        if waiting is not None:
            return waiting
    if writes:
        _LOGGER.warning(
            "run.gate_unreadable tenant=%s slug=%s channels=%s — a halted run will look "
            "finished; check whether LangGraph renamed %s",
            tenant,
            slug,
            sorted({channel for _, channel, _ in writes}),
            INTERRUPT_CHANNEL,
        )
    return None


async def arun_campaign(
    settings: Settings,
    tenant: str,
    slug: str,
    *,
    stage: str | None = None,
    run_id: str | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    web_backend: WebSearchTool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    document_store: DocumentStore | None = None,
    deliverable_store: DeliverableStore | None = None,
    usage_ledger: UsageLedger | None = None,
    questionnaire: Questionnaire | None = None,
    resume: Command | None = None,
    feedback: str | None = None,
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
        tenant: The tenant name.
        slug: The campaign slug.
        stage: The single stage to run, or ``None`` for the full pipeline.
        run_id: The id used as the trace filename; a fresh id is generated when
            ``None``. The API supplies one up front so it can register and return
            the run before the pipeline starts.
        on_event: An optional callback invoked with each progress event.
        web_backend: The web backend for agents that declare web tools.
        checkpointer: An optional checkpointer.
        document_store: The store tenant documents resolve through, or ``None``
            for the filesystem default.
        deliverable_store: The store deliverable versions are appended to, or
            ``None`` for the filesystem default.
        usage_ledger: The Usage Ledger every model call is checked against and
            charged to, or ``None`` to run uncharged. Checking inside the graph
            is what stops a run already in flight from spending past an
            allowance it was within when it started (ADR-0020).
        questionnaire: The published question set the Stage 0 gate enforces, so
            the graph gates on the same rule as the entrypoint that launched it
            (ADR-0026). ``None`` falls back to the code-shipped seed set, which
            is what a deployment with no database published serves.
        resume: A :class:`~langgraph.types.Command` carrying a person's decision
            at an Approval Gate, which continues the checkpointed run from where
            it halted instead of starting a fresh one.
        feedback: What the person wants changed, when this run re-opens a stage
            they had already approved. Seeded onto the stage exactly as an
            Approval Gate refusal is, so re-opening revises the previous
            deliverable rather than starting from a blank page (ADR-0015).

    Returns:
        The structured campaign result. A run halted at an Approval Gate returns
        the work done so far rather than raising: it has not failed, it is
        waiting on a person (ADR-0015).

    Raises:
        GateError: If the run halted on the Stage 0 gate.
        PipelineError: If a prerequisite was missing or a deliverable never saved.
        GuardrailError: If a deliverable failed QA within the revision budget.
        QuotaExhaustedError: If the tenant's allowance ran out mid-run.
    """
    trace = _open_trace(settings, tenant, slug, run_id or new_run_id())
    run_log = _rel_log(settings, trace)
    _LOGGER.info("run.start tenant=%s slug=%s stage=%s run_log=%s", tenant, slug, stage, run_log)
    backend: WebSearchTool | None = None
    owns_backend = False
    try:
        backend, owns_backend = _resolve_web_backend(settings, web_backend)
        graph = _select_graph(
            settings,
            stage,
            web_backend=backend,
            checkpointer=checkpointer,
            document_store=document_store,
            deliverable_store=deliverable_store,
            usage_ledger=usage_ledger,
            questionnaire=questionnaire or SEED_QUESTIONNAIRE,
        )
        config = _config(tenant, slug, stage)
        inbound: Any = resume if resume is not None else _initial_state(tenant, slug, feedback)
        state, awaiting = await _drive(graph, inbound, config, trace, on_event)
        if awaiting is not None:
            _write_awaiting_summary(trace, awaiting, run_log)
        else:
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
    return _to_result(tenant, slug, state, run_log, awaiting)
