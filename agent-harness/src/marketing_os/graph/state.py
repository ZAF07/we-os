"""Graph state — the typed state threaded through the campaign StateGraph.

A single flat :class:`CampaignState` carries both campaign-level data (customer,
DNA, accumulated results, usage) and the per-stage working set for the QA loop
(the specialist conversation, the current verdict, and the retry counters). The
per-stage working keys are reset at each stage's entry node.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


def add_usage(current: dict[str, int], update: dict[str, int]) -> dict[str, int]:
    """Merge two token-usage maps by summing matching keys.

    Args:
        current: The accumulated usage so far.
        update: The usage delta to fold in.

    Returns:
        A new map whose values are the per-key sums of the inputs.
    """
    merged = dict(current)
    for key, value in update.items():
        merged[key] = merged.get(key, 0) + value
    return merged


class CampaignState(TypedDict, total=False):
    """The state object for the campaign graph.

    Attributes:
        customer: The customer name the campaign runs for.
        slug: The campaign slug and checkpoint thread key.
        dna_text: The loaded Customer DNA, populated by the gate node.
        governance: The assembled governance preamble, populated by the gate node.
        error: A structured error describing why the run halted, if it did.
        halt: Whether the run should short-circuit to the end.
        results: The accumulated per-stage result dicts in pipeline order.
        usage: The aggregated token usage across every model call.
        messages: The current stage's specialist conversation.
        deliverable_text: The current stage's saved deliverable text, if present.
        verdict: The current stage's latest QA verdict as a plain dict.
        qa_iterations: The current stage's completed QA revision rounds.
        save_retries: The current stage's completed save-retry prompts.
        route: The routing decision the review node produced for the router.
    """

    customer: str
    slug: str
    dna_text: str
    governance: str
    error: dict[str, Any] | None
    halt: bool
    results: Annotated[list[dict[str, Any]], operator.add]
    usage: Annotated[dict[str, int], add_usage]
    messages: Annotated[list[AnyMessage], add_messages]
    deliverable_text: str | None
    verdict: dict[str, Any] | None
    qa_iterations: int
    save_retries: int
    route: str
