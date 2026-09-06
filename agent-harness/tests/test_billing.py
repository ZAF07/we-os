"""Billing: the check-then-charge ordering, driven without a graph.

The ordering is the rule (ADR-0020): checking after the call observes an
overspend rather than preventing one, and charging outside a ``finally`` lets a
cancelled call consume tokens for free. Both are silent when wrong — the money
is simply gone — so they are asserted here directly against
:func:`~marketing_os.billing.billed_call` rather than inferred from a run.
"""

from __future__ import annotations

import asyncio

import pytest

from conftest import SLUG, TENANT
from marketing_os.adapters.usage import InMemoryUsageLedger
from marketing_os.billing import billed_call
from marketing_os.config import Settings
from marketing_os.errors import QuotaExhaustedError
from marketing_os.governance.pipeline import PIPELINE_BY_KEY
from marketing_os.graph.state import CampaignState
from marketing_os.schemas import Usage

pytestmark = pytest.mark.asyncio

STAGE = PIPELINE_BY_KEY["research"]
MODEL = "counted-model"
RATE = 0.001


def _state() -> CampaignState:
    """Build the minimal campaign state a billed call reads.

    Returns:
        A state naming the tenant charged and the campaign charged for.
    """
    return {"tenant": TENANT, "slug": SLUG}  # type: ignore[typeddict-item]


def _ledger(allowance: float) -> InMemoryUsageLedger:
    """Build a ledger pricing the scripted model at a round rate.

    Args:
        allowance: What the tenant may spend before work is refused.

    Returns:
        The ledger under test.
    """
    settings = Settings(token_rates={MODEL: RATE}, usage_allowance=allowance)
    return InMemoryUsageLedger(settings)


async def test_an_exhausted_tenant_is_refused_before_the_call_is_made() -> None:
    """The check precedes the call, so no model runs on a spent allowance."""
    ledger = _ledger(allowance=1.0)
    ledger.record(
        TENANT,
        slug=SLUG,
        stage_key="research",
        model=MODEL,
        usage=Usage(input_tokens=2000),
    )
    assert ledger.consumption(TENANT).exhausted, "the fixture did not spend the allowance"
    called = False

    async def call() -> str:
        nonlocal called
        called = True
        return "ok"

    with pytest.raises(QuotaExhaustedError):
        await billed_call(ledger, _state(), STAGE, call)

    assert not called, "the model was called for a tenant who cannot pay for it"


async def test_a_call_that_raises_is_still_charged() -> None:
    """The charge runs in a ``finally``: a failed call still consumed tokens."""
    ledger = _ledger(allowance=100.0)

    async def call() -> str:
        raise RuntimeError("provider exploded")

    with pytest.raises(RuntimeError, match="provider exploded"):
        await billed_call(ledger, _state(), STAGE, call)

    assert ledger.entries(TENANT), "the failed call wrote no ledger entry"


async def test_a_cancelled_call_is_still_charged() -> None:
    """Cancelling must not be a way to consume tokens for free."""
    ledger = _ledger(allowance=100.0)
    entered = asyncio.Event()

    async def call() -> str:
        entered.set()
        await asyncio.sleep(60)
        return "never"

    task = asyncio.create_task(billed_call(ledger, _state(), STAGE, call))
    await asyncio.wait_for(entered.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert ledger.entries(TENANT), "the cancelled call wrote no ledger entry"


async def test_a_successful_call_returns_its_result_and_its_usage() -> None:
    """The caller gets back what it awaited, plus what the call cost."""
    ledger = _ledger(allowance=100.0)

    async def call() -> str:
        return "the verdict"

    result, usage = await billed_call(ledger, _state(), STAGE, call)

    assert result == "the verdict"
    assert set(usage) == {
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    }


async def test_a_run_without_a_ledger_is_not_refused() -> None:
    """An uncharged run is legal (ADR-0020) and must not fail closed."""

    async def call() -> str:
        return "ok"

    result, usage = await billed_call(None, _state(), STAGE, call)

    assert result == "ok"
    assert usage["input_tokens"] == 0
