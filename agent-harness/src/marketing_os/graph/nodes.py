"""Graph nodes — the gate, per-stage specialist, and per-stage QA review.

Each stage contributes three nodes wired by :mod:`marketing_os.graph.graph`:

* ``<stage>__enter`` validates the prerequisite, resets the per-stage working
  state, and seeds the task (with the Customer DNA) as the first message.
* ``<stage>__specialist`` runs the specialist agent's tool-use loop and folds its
  token usage into state.
* ``<stage>__review`` verifies the deliverable was saved (forcing a save-retry if
  not), scores it against the rubric, and records the routing decision.

Routing decisions are stored on ``state["route"]`` and read by the router
functions so the branching logic lives in one place.
"""

from __future__ import annotations

from typing import Any, Protocol

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.runnables import Runnable
from langgraph.config import get_stream_writer
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from marketing_os.adapters.observability import get_logger
from marketing_os.config import Settings
from marketing_os.governance import load_governance
from marketing_os.governance.gate import check_gate
from marketing_os.governance.pipeline import Stage, deliverable_path, prerequisite_met
from marketing_os.graph.state import CampaignState
from marketing_os.ports import Reviewer
from marketing_os.schemas import StageResult

_LOGGER = get_logger("marketing_os.graph")

_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


class CampaignNode(Protocol):
    """A graph node mapping the campaign state to a partial state update.

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


def make_gate_node(settings: Settings) -> CampaignNode:
    """Build the Stage 0 gate node.

    Args:
        settings: The harness settings.

    Returns:
        A node that validates the DNA/goal gate and loads the DNA on success.
    """

    def gate_node(state: CampaignState) -> dict[str, Any]:
        """Run the DNA and goal gate, halting the run if it fails.

        Args:
            state: The campaign state carrying ``customer`` and ``slug``.

        Returns:
            A state update: the loaded DNA and governance on success, or an error
            and halt flag on failure.
        """
        customer = state["customer"]
        slug = state["slug"]
        _emit("gate.start", customer=customer, slug=slug)
        report = check_gate(settings, customer, slug)
        if not report.ok:
            _emit("gate.failed", customer=customer, slug=slug, issues=report.all_issues)
            return {
                "error": {"type": "gate", "issues": list(report.all_issues)},
                "halt": True,
            }
        dna_text = (settings.customers_dir / customer / "dna.md").read_text(encoding="utf-8")
        (settings.campaigns_dir / slug).mkdir(parents=True, exist_ok=True)
        _emit("gate.passed", customer=customer, slug=slug)
        return {
            "dna_text": dna_text,
            "governance": load_governance(settings),
            "halt": False,
            "error": None,
            "usage": dict.fromkeys(_USAGE_KEYS, 0),
        }

    return gate_node


def make_enter_node(settings: Settings, stage: Stage) -> CampaignNode:
    """Build a stage's entry node.

    Args:
        settings: The harness settings.
        stage: The pipeline stage this node enters.

    Returns:
        A node that enforces the prerequisite and seeds the stage task.
    """

    def enter_node(state: CampaignState) -> dict[str, Any]:
        """Validate the prerequisite and seed the stage's task message.

        Args:
            state: The campaign state carrying the customer, slug, and DNA.

        Returns:
            A state update seeding a fresh specialist conversation, or an error
            and halt flag if the prerequisite deliverable is missing.
        """
        slug = state["slug"]
        customer = state["customer"]
        if not prerequisite_met(settings, slug, stage):
            _emit("stage.blocked", stage=stage.key, prerequisite=stage.prerequisite)
            return {
                "error": {
                    "type": "pipeline",
                    "stage": stage.key,
                    "prerequisite": stage.prerequisite,
                },
                "halt": True,
                "route": "end",
            }
        _emit("stage.start", stage=stage.key, agent=stage.agent)
        task = stage.task.format(
            goal_path=f"campaigns/{slug}/goal.md",
            dna_path=f"customers/{customer}/dna.md",
            prereq_path=(f"campaigns/{slug}/{stage.prerequisite}" if stage.prerequisite else ""),
            deliverable_path=str(
                deliverable_path(settings, slug, stage).relative_to(settings.root)
            ),
        )
        seed = (
            "# Customer DNA (ground every recommendation in this; never invent "
            f"what it omits)\n\n{state['dna_text']}\n\n# Your task\n\n{task}"
        )
        return {
            "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), HumanMessage(seed)],
            "qa_iterations": 0,
            "save_retries": 0,
            "verdict": None,
            "deliverable_text": None,
            "route": "specialist",
        }

    return enter_node


def make_specialist_node(settings: Settings, stage: Stage, agent: Runnable) -> CampaignNode:
    """Build a stage's specialist node.

    Args:
        settings: The harness settings (for the recursion budget).
        stage: The pipeline stage this node runs.
        agent: The compiled specialist agent for the stage.

    Returns:
        A node that runs the specialist's tool-use loop and folds in token usage.
    """
    recursion_limit = 2 * settings.max_steps + 1

    def specialist_node(state: CampaignState) -> dict[str, Any]:
        """Run the specialist agent over the current stage conversation.

        Args:
            state: The campaign state carrying the specialist ``messages``.

        Returns:
            A state update with the specialist's new messages and token usage.
        """
        inbound = list(state["messages"])
        with get_usage_metadata_callback() as callback:
            result = agent.invoke(
                {"messages": inbound},
                config={
                    "recursion_limit": recursion_limit,
                    "run_name": f"specialist:{stage.key}",
                },
            )
        produced = result["messages"][len(inbound) :]
        return {"messages": produced, "usage": _usage_delta(callback)}

    return specialist_node


def make_review_node(settings: Settings, stage: Stage, reviewer: Reviewer) -> CampaignNode:
    """Build a stage's QA review node.

    Args:
        settings: The harness settings (for the QA budget).
        stage: The pipeline stage this node reviews.
        reviewer: The QA reviewer scoring the deliverable.

    Returns:
        A node that verifies the save, scores the deliverable, and routes.
    """
    budget = settings.max_qa_iterations

    def review_node(state: CampaignState) -> dict[str, Any]:
        """Verify the deliverable was saved, score it, and set the route.

        Args:
            state: The campaign state after the specialist ran.

        Returns:
            A state update carrying the routing decision and, depending on the
            outcome, a revision message, a recorded stage result, or an error.
        """
        path = deliverable_path(settings, state["slug"], stage)
        rel = path.relative_to(settings.root)
        if not path.is_file():
            return _handle_missing_deliverable(state, stage, str(rel), budget)

        text = path.read_text(encoding="utf-8")
        with get_usage_metadata_callback() as callback:
            verdict = reviewer.review(stage.key, text)
        qa_iterations = state.get("qa_iterations", 0)
        discrepancies = [d.model_dump() for d in verdict.discrepancies]
        _emit(
            "stage.review",
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
                deliverable_path=str(rel),
                qa_iterations=qa_iterations,
                save_retries=state.get("save_retries", 0),
                verdict=verdict,
                approved=True,
            )
            _emit("stage.done", stage=stage.key, deliverable=str(rel), qa_iterations=qa_iterations)
            return {
                "deliverable_text": text,
                "verdict": verdict.model_dump(),
                "results": [result.model_dump()],
                "usage": usage,
                "route": "advance",
            }

        if qa_iterations >= budget:
            result = StageResult(
                stage=stage.key,
                deliverable_path=str(rel),
                qa_iterations=qa_iterations,
                save_retries=state.get("save_retries", 0),
                verdict=verdict,
                approved=False,
            )
            _emit(
                "stage.failed",
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

        return {
            "messages": [HumanMessage(verdict.as_revision_instruction())],
            "verdict": verdict.model_dump(),
            "qa_iterations": qa_iterations + 1,
            "usage": usage,
            "route": "revise",
        }

    return review_node


def _handle_missing_deliverable(
    state: CampaignState, stage: Stage, rel: str, budget: int
) -> dict[str, Any]:
    """Force a save-retry, or fail the stage once the retry budget is spent.

    Args:
        state: The campaign state after the specialist ran.
        stage: The stage whose deliverable is missing.
        rel: The repo-relative deliverable path the specialist must write.
        budget: The maximum number of save-retry prompts allowed.

    Returns:
        A state update that either re-prompts the specialist to save or halts.
    """
    save_retries = state.get("save_retries", 0)
    if save_retries >= budget:
        _emit("stage.failed", stage=stage.key, reason="not-saved")
        return {
            "error": {"type": "save", "stage": stage.key, "deliverable": rel},
            "halt": True,
            "route": "fail",
        }
    _emit("stage.save_retry", stage=stage.key, attempt=save_retries + 1)
    return {
        "messages": [
            HumanMessage(
                "You have not saved your deliverable. Save it now to "
                f"{rel} using the write_file tool, then stop."
            )
        ],
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
        ``"revise"``, ``"advance"``, or ``"fail"``.
    """
    return state.get("route", "fail")
