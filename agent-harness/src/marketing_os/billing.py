"""Billing — checking an allowance, making a billable call, and charging for it.

The check-then-charge ordering is load-bearing (ADR-0020): recording without
checking first observes an overspend rather than preventing one. That ordering
lives here, in one function, so no call site can get it wrong — and so the
tenant is refused *before* a model call rather than billed for one they could
not afford.

Billing is domain logic, not graph wiring. Keeping it above the adapter layer is
what lets the rule grow — per-model rates, per-stage budgets, a soft cap that
warns before it halts — without editing the LangGraph nodes that happen to call
it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from langchain_core.callbacks import get_usage_metadata_callback

from marketing_os.governance.pipeline import Stage
from marketing_os.graph.state import CampaignState
from marketing_os.ports import UsageLedger
from marketing_os.schemas import Usage

_Result = TypeVar("_Result")
"""The billable call's result type: billing does not care what it is."""

USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def usage_delta(callback: Any) -> dict[str, int]:
    """Reduce a usage-metadata callback into the harness's four-key usage map.

    Args:
        callback: A usage-metadata callback whose ``usage_metadata`` maps model
            names to per-call token counts.

    Returns:
        A map summing input, output, and cache token counts across every model.
    """
    total = dict.fromkeys(USAGE_KEYS, 0)
    for meta in (getattr(callback, "usage_metadata", None) or {}).values():
        total["input_tokens"] += meta.get("input_tokens", 0)
        total["output_tokens"] += meta.get("output_tokens", 0)
        details = meta.get("input_token_details") or {}
        total["cache_read_input_tokens"] += details.get("cache_read", 0)
        total["cache_creation_input_tokens"] += details.get("cache_creation", 0)
    return total


def billed_model(callback: Any) -> str:
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


def charge(
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
            which is what keeps the graph tests usable.
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
        model=billed_model(callback),
        usage=Usage(**delta),
    )


async def billed_call(
    ledger: UsageLedger | None,
    state: CampaignState,
    stage: Stage,
    call: Callable[[], Awaitable[_Result]],
) -> tuple[_Result, dict[str, int]]:
    """Check the allowance, await one billable call, and charge for what it used.

    The whole sequence in one place, because its order is the rule: the check
    runs before ``call``, so an exhausted tenant makes no model call at all, and
    the charge runs in a ``finally``, so a call that raises or is cancelled is
    still billed for the tokens it consumed (ADR-0020). A caller cannot reorder
    what it does not spell out.

    Generic over the result type because the callers differ — a specialist
    awaits its agent, the reviewer its verdict — and neither result shape is
    billing's business.

    Args:
        ledger: The Usage Ledger to check and charge, or ``None`` to run
            uncharged, which is what a deployment without one does.
        state: The campaign state naming the tenant and campaign.
        stage: The stage the call is made on behalf of.
        call: The billable work to await, taking no arguments.

    Returns:
        The call's result, and the token counts it consumed.

    Raises:
        QuotaExhaustedError: If the tenant's allowance is already spent, before
            any call is made. Turning that refusal into a halted run is the
            graph's business, not billing's, so it is raised rather than shaped.
    """
    if ledger is not None:
        ledger.check(state["tenant"])
    with get_usage_metadata_callback() as callback:
        try:
            result = await call()
        finally:
            delta = usage_delta(callback)
            charge(ledger, state, stage, callback, delta)
    return result, delta
