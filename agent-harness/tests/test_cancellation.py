"""Cancellation: a run on the async path aborts its in-flight LLM call.

The async graph path (ADR-0009) exists so a run launched as an ``asyncio.Task``
can be cancelled such that the ``CancelledError`` lands *inside* the specialist's
awaited LLM call — aborting the in-flight provider request rather than only
stopping between stages. These tests drive the compiled graph with a model whose
``ainvoke`` blocks on an event the test controls, so cancellation is observable
without any network.
"""

from __future__ import annotations

import asyncio

import pytest

from conftest import PASS_VERDICT, BlockingChatModel, FakeReviewer
from marketing_os.config import Settings
from marketing_os.graph.graph import build_single_stage_graph


def _config(thread: str) -> dict:
    """Build an invoke config with a thread id and a generous recursion limit.

    Args:
        thread: The checkpoint thread id.

    Returns:
        The runnable config.
    """
    return {"configurable": {"thread_id": thread}, "recursion_limit": 50}


async def test_cancel_aborts_in_flight_llm_call(settings: Settings) -> None:
    model = BlockingChatModel()
    graph = build_single_stage_graph(
        settings, "research", model=model, reviewer=FakeReviewer([PASS_VERDICT])
    )
    task = asyncio.create_task(
        graph.ainvoke({"customer": "acme", "slug": "acme"}, config=_config("cancel"))
    )

    await asyncio.wait_for(model.entered.wait(), timeout=5)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert model.was_cancelled is True, "the in-flight LLM call was not cancelled"
    assert not (settings.campaigns_dir / "acme" / "research.md").is_file()
