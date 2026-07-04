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
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from conftest import PASS_VERDICT, FakeReviewer
from marketing_os.config import Settings
from marketing_os.graph.graph import build_single_stage_graph


class _BlockingChatModel(BaseChatModel):
    """A chat model whose ``ainvoke`` blocks forever until the task is cancelled.

    It signals when the LLM call is in-flight via :attr:`entered` and records
    whether that awaited call was cancelled via :attr:`was_cancelled`, so a test
    can prove that cancelling the run's task aborts the in-flight request rather
    than leaving it running.
    """

    entered: asyncio.Event = Field(default_factory=asyncio.Event)
    was_cancelled: bool = False
    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        """Return the model type identifier."""
        return "blocking"

    def bind_tools(self, tools: Any, **kwargs: Any) -> _BlockingChatModel:
        """Ignore tool binding and return self, since the reply never arrives.

        Args:
            tools: The tools being bound (ignored).
            **kwargs: Additional binding arguments (ignored).

        Returns:
            This model instance.
        """
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Fail loudly if invoked synchronously; this model is async-only.

        Args:
            messages: The conversation so far (unused).
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Raises:
            NotImplementedError: Always, to prove the async path is exercised.
        """
        raise NotImplementedError("blocking model is async-only")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Signal that the LLM call is in-flight, then block until cancelled.

        Args:
            messages: The conversation so far (unused).
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            A chat result — never reached, since the call blocks forever.

        Raises:
            asyncio.CancelledError: When the run's task is cancelled mid-call.
        """
        self.entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.was_cancelled = True
            raise
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="unreachable"))])


def _config(thread: str) -> dict:
    """Build an invoke config with a thread id and a generous recursion limit.

    Args:
        thread: The checkpoint thread id.

    Returns:
        The runnable config.
    """
    return {"configurable": {"thread_id": thread}, "recursion_limit": 50}


async def test_cancel_aborts_in_flight_llm_call(settings: Settings) -> None:
    model = _BlockingChatModel()
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
