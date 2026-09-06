"""Graph nodes — the gate, per-stage specialist, QA review, and Approval Gate.

Each stage contributes four nodes wired by :mod:`marketing_os.graph.graph`:

* ``<stage>__enter`` validates the prerequisite, resets the per-stage working
  state, and seeds the task (with the Brand DNA) as the first message.
* ``<stage>__specialist`` checks the tenant's allowance, runs the specialist
  agent's tool-use loop, and records what it cost.
* ``<stage>__review`` verifies the deliverable was saved (forcing a save-retry if
  not), scores it against the rubric, records the version it produced, and sets
  the routing decision.
* ``<stage>__approval`` halts a ``human``-policy stage on a LangGraph
  ``interrupt()`` until a person approves it or sends it back with feedback.

The allowance is checked in these nodes rather than only at the HTTP edge,
because they are where the billable call actually happens: an endpoint is not
the only thing that can drive the graph, and a run already in flight can exhaust
an allowance it was within when it started. Recording happens immediately after
each call, so a run cancelled mid-pipeline is still charged for the work it did
(ADR-0020).

The Approval Gate is deliberately not the QA reviewer. The reviewer is a model
scoring a deliverable against a Guardrail; the gate is a person's decision. Both
can send a stage back, but only the gate blocks progress on a human (ADR-0015).

Routing decisions are stored on ``state["route"]`` and read by the router
functions so the branching logic lives in one place.
"""

from __future__ import annotations

from typing import Any, Protocol

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import BaseMessage, HumanMessage, RemoveMessage
from langchain_core.runnables import Runnable
from langgraph.config import get_stream_writer
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.types import interrupt

from marketing_os.adapters.deliverables import (
    HUMAN_FEEDBACK,
    REVIEWER_FEEDBACK,
    human_revisions_used,
)
from marketing_os.adapters.observability import get_logger
from marketing_os.config import Settings
from marketing_os.errors import QuotaExhaustedError
from marketing_os.governance.gate import check_gate
from marketing_os.governance.pipeline import HUMAN, Stage, prerequisite_met, stage_document
from marketing_os.graph.state import CampaignState
from marketing_os.ports import DeliverableStore, DocumentStore, Reviewer, UsageLedger
from marketing_os.schemas import ApprovalDecision, Questionnaire, StageResult, Usage

_LOGGER = get_logger("marketing_os.graph")

_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


class CampaignNode(Protocol):
    """A synchronous graph node mapping the campaign state to a state update.

    The single parameter is named ``state`` (rather than using a positional-only
    ``Callable[[CampaignState], ...]`` alias) so the node satisfies LangGraph's
    node protocol, which requires a keyword-addressable ``state`` parameter.
    """

    def __call__(self, state: CampaignState) -> dict[str, Any]:
        """Run the node.

        Args:
            state: The current campaign state.

        Returns:
            The partial state update produced by the node.
        """
        ...


class AsyncCampaignNode(Protocol):
    """An async graph node mapping the campaign state to a state update.

    The specialist and review nodes are ``async def`` (per ADR-0009) so their LLM
    calls are awaited on the event loop and abort when the run's task is
    cancelled. LangGraph awaits these coroutine nodes on the async run path.
    """

    async def __call__(self, state: CampaignState) -> dict[str, Any]:
        """Run the node.

        Args:
            state: The current campaign state.

        Returns:
            The partial state update produced by the node.
        """
        ...


def _emit(event: str, **data: Any) -> None:
    """Emit a semantic progress event to any active custom stream.

    The event is dropped silently when the graph is not being streamed in custom
    mode, and never raises out of a node.

    Args:
        event: The event name, for example ``"stage.review"``.
        **data: Additional fields describing the event.
    """
    _LOGGER.info("%s %s", event, _format_event(data))
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return
    writer({"event": event, **data})


def _format_event(data: dict[str, Any]) -> str:
    """Render an event payload as a compact, readable log fragment.

    Args:
        data: The event fields.

    Returns:
        A ``key=value`` string; discrepancy lists are summarised by rubric point.
    """
    parts: list[str] = []
    for key, value in data.items():
        if key == "discrepancies" and isinstance(value, list):
            points = "; ".join(
                str(item.get("rubric_point", "?")) for item in value if isinstance(item, dict)
            )
            parts.append(f"discrepancies=[{points}]")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def _usage_delta(callback: Any) -> dict[str, int]:
    """Reduce a usage-metadata callback into the harness's four-key usage map.

    Args:
        callback: A usage-metadata callback whose ``usage_metadata`` maps model
            names to per-call token counts.

    Returns:
        A map summing input, output, and cache token counts across every model.
    """
    total = dict.fromkeys(_USAGE_KEYS, 0)
    for meta in (getattr(callback, "usage_metadata", None) or {}).values():
        total["input_tokens"] += meta.get("input_tokens", 0)
        total["output_tokens"] += meta.get("output_tokens", 0)
        details = meta.get("input_token_details") or {}
        total["cache_read_input_tokens"] += details.get("cache_read", 0)
        total["cache_creation_input_tokens"] += details.get("cache_creation", 0)
    return total


def _billed_model(callback: Any) -> str:
    """Return the model a call was billed against, for the ledger entry.

    Args:
        callback: A usage-metadata callback whose ``usage_metadata`` maps model
            names to per-call token counts.

    Returns:
        The model name the provider reported, or the empty string when it
        reported none — an unnamed model is still charged, at the default rate.
    """
    reported = getattr(callback, "usage_metadata", None) or {}
    return next(iter(reported), "")


def _charge(
    ledger: UsageLedger | None,
    state: CampaignState,
    stage: Stage,
    callback: Any,
    delta: dict[str, int],
) -> None:
    """Record what one model call cost, against the tenant that caused it.

    Args:
        ledger: The Usage Ledger to charge, or ``None`` when the deployment runs
            without one — a run then proceeds uncharged rather than failing,
            which is what keeps the CLI and the graph tests usable.
        state: The campaign state naming the tenant and campaign.
        stage: The stage the call was made on behalf of.
        callback: The usage-metadata callback the call ran under.
        delta: The token counts the call consumed.
    """
    if ledger is None:
        return
    ledger.record(
        state["tenant"],
        slug=state["slug"],
        stage_key=stage.key,
        model=_billed_model(callback),
        usage=Usage(**delta),
    )


def _quota_halt(exc: QuotaExhaustedError, stage: Stage, slug: str) -> dict[str, Any]:
    """Halt the run because the tenant's allowance is spent.

    Recorded as a halting state error rather than raised, so it travels the same
    path every other halt does and reaches the caller as the typed 402 through
    :func:`~marketing_os.errors.exception_from_state_error`.

    Args:
        exc: The refusal the ledger raised.
        stage: The stage whose call was refused.
        slug: The campaign slug.

    Returns:
        A state update halting the run.
    """
    _emit("stage.quota_exhausted", slug=slug, stage=stage.key, used=exc.used)
    return {
        "error": {
            "type": "quota",
            "stage": stage.key,
            "used": exc.used,
            "allowance": exc.allowance,
        },
        "halt": True,
        "route": "fail",
    }


def _compose_seed(dna_text: str, body: str) -> str:
    """Compose a specialist seed message from the DNA and a task/instruction body.

    Args:
        dna_text: The Brand DNA to ground the work in.
        body: The task or revision instructions.

    Returns:
        The seed message text.
    """
    return (
        "# Brand DNA (ground every recommendation in this; never invent "
        f"what it omits)\n\n{dna_text}\n\n{body}"
    )


def _fresh_conversation(dna_text: str, body: str) -> list[BaseMessage]:
    """Build a reset conversation seeded with a single clean human turn.

    Resetting the messages before each specialist attempt keeps every attempt a
    short, single-turn conversation, so a multi-round tool-call history is never
    re-sent to the model (which DeepSeek V4 thinking mode rejects).

    Args:
        dna_text: The Brand DNA to ground the work in.
        body: The task or revision instructions.

    Returns:
        A ``RemoveMessage``-then-``HumanMessage`` list that clears prior turns and
        seeds the new one.
    """
    return [RemoveMessage(id=REMOVE_ALL_MESSAGES), HumanMessage(_compose_seed(dna_text, body))]


def _path_anchor(slug: str) -> str:
    """Build a prominent reminder of the campaign slug and its path prefix.

    Prepended to every specialist seed so the exact slug the model must type in
    tool-call paths is stated redundantly and hard to corrupt, rather than
    appearing only once inside a single deliverable path.

    Args:
        slug: The campaign slug.

    Returns:
        A short markdown block naming the slug and the path prefix to use.
    """
    return (
        f"# Campaign\n\nThis campaign's slug is `{slug}`. Every file you read or write "
        f"lives under `campaigns/{slug}/`. Use this exact slug, character for character, "
        "in every tool-call path — never alter, abbreviate, or guess it."
    )


def _stage_task(slug: str, stage: Stage) -> str:
    """Format the task brief for a stage with its document paths filled in.

    The paths are tenant-relative logical document paths, not repository paths:
    the Brand DNA is simply ``dna.md``, because a tenant has exactly one, and the
    document store resolves it for whichever tenant the run belongs to. The
    tenant therefore never appears in a path the model can see or alter.

    Args:
        slug: The campaign slug.
        stage: The pipeline stage.

    Returns:
        The formatted task brief.
    """
    return stage.task.format(
        goal_path=f"campaigns/{slug}/goal.md",
        dna_path="dna.md",
        prereq_path=(f"campaigns/{slug}/{stage.prerequisite}" if stage.prerequisite else ""),
        deliverable_path=stage_document(slug, stage),
    )


def _stage_seed_body(slug: str, stage: Stage, feedback: str | None, previous: str | None) -> str:
    """Build the specialist's seed body for a stage attempt.

    A first attempt is seeded with the stage's task. An attempt following an
    Approval Gate refusal — or a re-opening of a stage the owner had already
    approved — is seeded with the person's written feedback and the draft they
    are reacting to, so the specialist revises what was rejected rather than
    starting from a blank page and losing everything that already passed.

    Args:
        slug: The campaign slug.
        stage: The pipeline stage being entered.
        feedback: The person's feedback from the Approval Gate, if any.
        previous: The draft the person refused, if it is still on state.

    Returns:
        The seed body to compose with the Brand DNA.
    """
    task = _stage_task(slug, stage)
    if not feedback:
        return f"{_path_anchor(slug)}\n\n# Your task\n\n{task}"
    draft = f"## Previous draft\n\n{previous}\n\n" if previous else ""
    return (
        f"{_path_anchor(slug)}\n\n# Your task\n\n{task}\n\n"
        f"# Feedback from the business owner\n\nThe owner reviewed your previous "
        f"work and sent it back. Address their feedback in full, keeping everything "
        f"they did not object to.\n\n{draft}"
        f"## What they asked for\n\n{feedback}"
    )


def make_gate_node(
    settings: Settings, store: DocumentStore, questionnaire: Questionnaire
) -> CampaignNode:
    """Build the Stage 0 gate node.

    Args:
        settings: The harness settings.
        store: The document store the DNA and goal resolve through.
        questionnaire: The published question set whose Required questions the
            gate enforces, so the graph gates on the same rule as the entrypoint
            that launched it.

    Returns:
        A node that validates the DNA/goal gate and loads the DNA on success.
    """

    def gate_node(state: CampaignState) -> dict[str, Any]:
        """Run the DNA and goal gate, halting the run if it fails.

        Args:
            state: The campaign state carrying ``tenant`` and ``slug``.

        Returns:
            A state update: the loaded DNA on success, or an error and halt flag
            on failure.
        """
        tenant = state["tenant"]
        slug = state["slug"]
        _emit("gate.start", tenant=tenant, slug=slug)
        report = check_gate(settings, tenant, slug, store=store, questionnaire=questionnaire)
        if not report.ok:
            _emit("gate.failed", tenant=tenant, slug=slug, issues=report.all_issues)
            return {
                "error": {"type": "gate", "issues": list(report.all_issues)},
                "halt": True,
            }
        dna_text = store.read(tenant, "dna.md")
        _emit("gate.passed", tenant=tenant, slug=slug)
        return {
            "dna_text": dna_text,
            "halt": False,
            "error": None,
            "usage": dict.fromkeys(_USAGE_KEYS, 0),
        }

    return gate_node


def make_enter_node(stage: Stage, store: DocumentStore) -> CampaignNode:
    """Build a stage's entry node.

    Args:
        stage: The pipeline stage this node enters.
        store: The document store the prerequisite deliverable resolves through.

    Returns:
        A node that enforces the prerequisite and seeds the stage task.
    """

    def enter_node(state: CampaignState) -> dict[str, Any]:
        """Validate the prerequisite and seed the stage's task message.

        Args:
            state: The campaign state carrying the tenant, slug, and DNA.

        Returns:
            A state update seeding a fresh specialist conversation — carrying the
            person's feedback when the stage was sent back from its Approval Gate
            — or an error and halt flag if the prerequisite deliverable is missing.

            ``human_feedback`` is deliberately **not** cleared here: the review
            node needs it to record on the version this attempt produces. The
            Approval Gate clears it once the person has decided again.
        """
        slug = state["slug"]
        tenant = state["tenant"]
        if not prerequisite_met(store, tenant, slug, stage):
            _emit("stage.blocked", slug=slug, stage=stage.key, prerequisite=stage.prerequisite)
            return {
                "error": {
                    "type": "pipeline",
                    "stage": stage.key,
                    "prerequisite": stage.prerequisite,
                },
                "halt": True,
                "route": "end",
            }
        _emit("stage.start", slug=slug, stage=stage.key, agent=stage.agent)
        feedback = state.get("human_feedback")
        previous = _previous_draft(store, state, tenant, slug, stage)
        task_body = _stage_seed_body(slug, stage, feedback, previous)
        return {
            "messages": _fresh_conversation(state["dna_text"], task_body),
            "qa_iterations": 0,
            "save_retries": 0,
            "verdict": None,
            "deliverable_text": None,
            "route": "specialist",
        }

    return enter_node


def _previous_draft(
    store: DocumentStore, state: CampaignState, tenant: str, slug: str, stage: Stage
) -> str | None:
    """Return the draft a revising attempt should work from, if there is one.

    Only an attempt carrying the owner's feedback has a draft to react to, so a
    first attempt reads nothing. Within a run the refused draft is already on
    state. A re-opened stage starts a **fresh** run, so state carries nothing —
    the draft the owner is reacting to is the deliverable currently saved.
    Reading it here is what makes re-opening a revision of existing work rather
    than a rewrite from scratch (ADR-0015).

    Args:
        store: The document store the saved deliverable resolves through.
        state: The current campaign state.
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.
        stage: The stage being entered.

    Returns:
        The previous draft, or ``None`` when the stage has produced none.
    """
    if not state.get("human_feedback"):
        return None
    on_state = state.get("deliverable_text")
    if on_state:
        return on_state
    document = stage_document(slug, stage)
    if not store.exists(tenant, document):
        return None
    return store.read(tenant, document)


def make_specialist_node(
    settings: Settings,
    stage: Stage,
    agent: Runnable,
    ledger: UsageLedger | None = None,
) -> AsyncCampaignNode:
    """Build a stage's specialist node.

    Args:
        settings: The harness settings (for the recursion budget).
        stage: The pipeline stage this node runs.
        agent: The compiled specialist agent for the stage.
        ledger: The Usage Ledger the tenant's allowance is checked against and
            the call is charged to, or ``None`` to run uncharged.

    Returns:
        A node that checks the allowance, runs the specialist's tool-use loop,
        charges what it cost, and folds in token usage.
    """
    recursion_limit = 2 * settings.max_steps + 1

    async def specialist_node(state: CampaignState) -> dict[str, Any]:
        """Run the specialist agent over the current stage conversation.

        The allowance is checked **before** the agent is invoked, so an exhausted
        tenant makes no model call at all rather than one the ledger reports
        afterwards (ADR-0020). The agent's tool-use loop is awaited (``ainvoke``)
        so every LLM call runs on the event loop; cancelling the run's task
        aborts the in-flight LLM request inside the loop rather than only between
        stages (see ADR-0009). The run ``slug`` and ``tenant`` are passed into
        the agent state so the ``write_file`` tool can scope writes to
        ``campaigns/<slug>/`` under the right tenant at call time.

        Args:
            state: The campaign state carrying the specialist ``messages`` and slug.

        Returns:
            A state update with the specialist's new messages and token usage, or
            a halt when the tenant's allowance is spent.
        """
        if ledger is not None:
            try:
                ledger.check(state["tenant"])
            except QuotaExhaustedError as exc:
                return _quota_halt(exc, stage, state["slug"])
        inbound = list(state["messages"])
        with get_usage_metadata_callback() as callback:
            try:
                result = await agent.ainvoke(
                    {"messages": inbound, "slug": state["slug"], "tenant": state["tenant"]},
                    config={
                        "recursion_limit": recursion_limit,
                        "run_name": f"specialist:{stage.key}",
                    },
                )
            finally:
                _charge(ledger, state, stage, callback, _usage_delta(callback))
        produced = result["messages"][len(inbound) :]
        return {"messages": produced, "usage": _usage_delta(callback)}

    return specialist_node


def make_review_node(
    settings: Settings,
    stage: Stage,
    reviewer: Reviewer,
    store: DocumentStore,
    deliverables: DeliverableStore,
    ledger: UsageLedger | None = None,
) -> AsyncCampaignNode:
    """Build a stage's QA review node.

    Args:
        settings: The harness settings (for the QA budget).
        stage: The pipeline stage this node reviews.
        reviewer: The QA reviewer scoring the deliverable.
        store: The document store the deliverable resolves through.
        deliverables: The store each passing deliverable is versioned into.
        ledger: The Usage Ledger the tenant's allowance is checked against and
            the review call is charged to, or ``None`` to run uncharged. The
            reviewer is a model call like any other, so it is billable too —
            exempting it would let the QA loop spend beyond the allowance.

    Returns:
        A node that verifies the save, scores the deliverable, records its
        version, and routes.
    """
    budget = settings.max_qa_iterations

    async def review_node(state: CampaignState) -> dict[str, Any]:
        """Verify the deliverable was saved, score it, and set the route.

        The reviewer's LLM call is awaited (per ADR-0009) so it aborts if the
        run's task is cancelled mid-review, and the allowance is checked before
        it for the same reason the specialist's is: the review is a billable call.

        Args:
            state: The campaign state after the specialist ran.

        Returns:
            A state update carrying the routing decision and, depending on the
            outcome, a revision message, a recorded stage result, or an error.
        """
        slug = state["slug"]
        tenant = state["tenant"]
        rel = stage_document(slug, stage)
        if not store.exists(tenant, rel):
            return _handle_missing_deliverable(state, stage, rel, budget)

        if ledger is not None:
            try:
                ledger.check(tenant)
            except QuotaExhaustedError as exc:
                return _quota_halt(exc, stage, slug)

        text = store.read(tenant, rel)
        with get_usage_metadata_callback() as callback:
            try:
                verdict = await reviewer.areview(stage.key, text)
            finally:
                _charge(ledger, state, stage, callback, _usage_delta(callback))
        qa_iterations = state.get("qa_iterations", 0)
        discrepancies = [d.model_dump() for d in verdict.discrepancies]
        _emit(
            "stage.review",
            slug=slug,
            stage=stage.key,
            passed=verdict.passed,
            iteration=qa_iterations,
            summary=verdict.summary,
            discrepancies=discrepancies,
        )
        usage = _usage_delta(callback)

        if verdict.passed:
            result = StageResult(
                stage=stage.key,
                deliverable_path=rel,
                qa_iterations=qa_iterations,
                save_retries=state.get("save_retries", 0),
                verdict=verdict,
                approved=True,
            )
            version = _record_version(deliverables, state, stage, text)
            _emit(
                "stage.done",
                slug=slug,
                stage=stage.key,
                deliverable=rel,
                qa_iterations=qa_iterations,
                version=version,
            )
            return {
                "deliverable_text": text,
                "verdict": verdict.model_dump(),
                "results": [result.model_dump()],
                "usage": usage,
                "route": "approval" if stage.approval_policy == HUMAN else "advance",
            }

        if qa_iterations >= budget:
            result = StageResult(
                stage=stage.key,
                deliverable_path=rel,
                qa_iterations=qa_iterations,
                save_retries=state.get("save_retries", 0),
                verdict=verdict,
                approved=False,
            )
            _emit(
                "stage.failed",
                slug=slug,
                stage=stage.key,
                reason="qa",
                summary=verdict.summary,
                discrepancies=discrepancies,
            )
            return {
                "verdict": verdict.model_dump(),
                "results": [result.model_dump()],
                "usage": usage,
                "error": {
                    "type": "guardrail",
                    "stage": stage.key,
                    "summary": verdict.summary,
                    "discrepancies": discrepancies,
                },
                "halt": True,
                "route": "fail",
            }

        revise_body = (
            f"{_path_anchor(slug)}\n\n# Revision\n\nYour previous draft is "
            f"reproduced below. Resolve every issue listed, then save the revised "
            f"deliverable to `{rel}` with the write_file tool.\n\n"
            f"## Previous draft\n\n{text}\n\n"
            f"## Required changes\n\n{verdict.as_revision_instruction()}"
        )
        return {
            "messages": _fresh_conversation(state["dna_text"], revise_body),
            "verdict": verdict.model_dump(),
            "qa_iterations": qa_iterations + 1,
            "usage": usage,
            "route": "revise",
        }

    return review_node


def _record_version(
    deliverables: DeliverableStore, state: CampaignState, stage: Stage, text: str
) -> int:
    """Append the passing deliverable as a new immutable version.

    The feedback that prompted this attempt — a person's at the Approval Gate, or
    the QA reviewer's within the revision loop — is recorded on the version, so
    the history answers "why did this change?" rather than only "what changed?".
    Nothing is overwritten (ADR-0015).

    Args:
        deliverables: The store holding the version chain.
        state: The campaign state after the specialist ran.
        stage: The stage whose deliverable passed.
        text: The full deliverable markdown as saved.

    Returns:
        The version number assigned to this deliverable.
    """
    human_feedback = state.get("human_feedback")
    verdict = state.get("verdict")
    if human_feedback:
        feedback, source = human_feedback, HUMAN_FEEDBACK
    elif verdict and not verdict.get("passed"):
        feedback, source = str(verdict.get("summary", "")), REVIEWER_FEEDBACK
    else:
        feedback, source = None, None
    version = deliverables.append(
        state["tenant"],
        state["slug"],
        stage.key,
        text,
        feedback=feedback,
        feedback_source=source,
    )
    return version.version


def make_approval_node(
    settings: Settings, stage: Stage, deliverables: DeliverableStore
) -> CampaignNode:
    """Build a stage's Approval Gate node.

    Only reached by ``human``-policy stages. The node halts the run on a
    LangGraph ``interrupt()``, which suspends the graph at this point and
    persists it to the checkpointer — which is why a durable checkpointer is a
    hard prerequisite rather than a parallel chore (ADR-0015): a halted run must
    survive a restart and still be approvable afterwards.

    The revision cap is enforced **here**, in the graph, rather than only at the
    HTTP edge, so every driver of the pipeline is bound by it — an endpoint is
    not the only thing that can resume a run. Both the count shown to the person
    and the count the cap tests come from the deliverable's version chain, so
    there is one answer to "how many revisions have I used?" rather than two.

    Args:
        settings: The harness settings (for the per-deliverable revision cap).
        stage: The pipeline stage this gate guards.
        deliverables: The store the stage's version history is read from.

    Returns:
        A node that waits for a person's decision and routes on their answer.
    """
    cap = settings.max_revisions

    def approval_node(state: CampaignState) -> dict[str, Any]:
        """Halt until a person approves the stage or sends it back with feedback.

        Args:
            state: The campaign state after the stage passed QA.

        Returns:
            A state update routing to the next stage on approval, or back into
            this stage carrying the person's feedback on a refusal.
        """
        slug = state["slug"]
        spent = human_revisions_used(deliverables.history(state["tenant"], slug, stage.key))
        remaining = max(cap - spent, 0)
        _emit(
            "stage.awaiting_approval",
            slug=slug,
            stage=stage.key,
            revisions_used=spent,
            revisions_allowed=cap,
        )
        decision = ApprovalDecision(
            **interrupt(
                {
                    "stage": stage.key,
                    "deliverable": stage_document(slug, stage),
                    "revisions_used": spent,
                    "revisions_allowed": cap,
                }
            )
        )
        if decision.approved:
            _emit("stage.approved", slug=slug, stage=stage.key)
            return {"human_feedback": None, "route": "advance"}
        if remaining <= 0:
            _emit("stage.revision_limit", slug=slug, stage=stage.key, revisions_allowed=cap)
            return {
                "error": {"type": "revision_limit", "stage": stage.key, "limit": cap},
                "halt": True,
                "route": "fail",
            }
        _emit("stage.revision_requested", slug=slug, stage=stage.key, revision=spent + 1)
        return {"human_feedback": decision.feedback, "route": "revise"}

    return approval_node


def _handle_missing_deliverable(
    state: CampaignState, stage: Stage, rel: str, budget: int
) -> dict[str, Any]:
    """Force a save-retry, or fail the stage once the retry budget is spent.

    The retry re-seeds a fresh conversation with the full task and an explicit
    save instruction rather than appending to the prior transcript.

    Args:
        state: The campaign state after the specialist ran.
        stage: The stage whose deliverable is missing.
        rel: The repo-relative deliverable path the specialist must write.
        budget: The maximum number of save-retry prompts allowed.

    Returns:
        A state update that either re-prompts the specialist to save or halts.
    """
    slug = state["slug"]
    save_retries = state.get("save_retries", 0)
    if save_retries >= budget:
        _emit("stage.failed", slug=slug, stage=stage.key, reason="not-saved")
        return {
            "error": {"type": "save", "stage": stage.key, "deliverable": rel},
            "halt": True,
            "route": "fail",
        }
    _emit("stage.save_retry", slug=slug, stage=stage.key, attempt=save_retries + 1)
    task = _stage_task(slug, stage)
    save_body = (
        f"{_path_anchor(slug)}\n\n# Your task\n\n{task}\n\n# Important\n\nYou did NOT save "
        f"your deliverable. You MUST call the write_file tool to save it to {rel}, then stop."
    )
    return {
        "messages": _fresh_conversation(state["dna_text"], save_body),
        "save_retries": save_retries + 1,
        "route": "revise",
    }


def route_after_enter(state: CampaignState) -> str:
    """Route out of a stage's entry node.

    Args:
        state: The campaign state after the entry node ran.

    Returns:
        ``"specialist"`` to run the stage, or ``"end"`` to halt the run.
    """
    return state.get("route", "specialist")


def route_after_review(state: CampaignState) -> str:
    """Route out of a stage's review node.

    Args:
        state: The campaign state after the review node ran.

    Returns:
        ``"revise"``, ``"approval"``, ``"advance"``, or ``"fail"``.
    """
    return state.get("route", "fail")


def route_after_approval(state: CampaignState) -> str:
    """Route out of a stage's Approval Gate node.

    Args:
        state: The campaign state after the person decided.

    Returns:
        ``"advance"`` when approved, ``"revise"`` to re-run the stage with the
        feedback, or ``"fail"`` when the deliverable's revision cap is spent.
    """
    return state.get("route", "advance")
