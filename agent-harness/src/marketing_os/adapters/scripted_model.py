"""A scripted chat model, for driving the interface without calling a provider.

The end-to-end suite is about the *screens*: that a run reaches an Approval
Gate, that the deliverable renders, that approving resumes and revising appends
a version. None of that is a question about a language model, and answering it
with a real one would make the suite slow, costly, and non-deterministic — a
spec could fail because a model phrased something differently, which tells
nobody anything about the frontend.

So this adapter satisfies the same ``BaseChatModel`` port the real providers do
(ADR-0001), selected with ``MARKETING_OS_PROVIDER=scripted``. It writes a fixed
deliverable through the ``write_file`` tool and passes every QA review, so a run
walks the pipeline and halts at each gate exactly as it would in production.

Test-only. It is refused unless ``MARKETING_OS_ALLOW_SCRIPTED_MODEL=1``, so it
cannot be selected by a misconfigured deployment: a provider that silently
fabricates deliverables is far worse than one that fails to start.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda

from marketing_os.errors import ConfigError
from marketing_os.schemas import ReviewVerdict

PROVIDER_NAME = "scripted"
ENABLE_FLAG = "MARKETING_OS_ALLOW_SCRIPTED_MODEL"

_DELIVERABLE_BODY = (
    "# {stage}\n\n"
    "Written by the scripted model for the end-to-end suite.\n\n"
    "## Recommendation\n\n"
    "Lead with the coached first session, which is the thing the business "
    "offers that its alternatives do not.\n\n"
    "## Why\n\n"
    "The Brand DNA names beginners who find climbing gyms intimidating, and "
    "names included coaching as the reason customers choose this business.\n"
)


def _deliverable_path(messages: list[BaseMessage]) -> str:
    """Find the path the specialist was told to *save* its deliverable to.

    Every task prompt names several documents — the goal and the upstream
    deliverable it must read, then the one it must write — so picking the first
    path in the prompt writes over the campaign goal. The one to write is the
    one the "Save to ..." sentence names, which is always the last.

    Args:
        messages: The conversation so far.

    Returns:
        The deliverable path, or a fallback when no prompt names one.
    """
    found: list[str] = []
    for message in messages:
        content = message.content
        text = content if isinstance(content, str) else str(content)
        for token in text.replace("`", " ").split():
            cleaned = token.strip(".,;:'\"()[]")
            if cleaned.endswith(".md") and "campaigns/" in cleaned:
                found.append(cleaned)
    if not found:
        return "campaigns/unknown/deliverable.md"
    written = [path for path in found if not path.endswith("/goal.md")]
    return written[-1] if written else found[-1]


class ScriptedChatModel(BaseChatModel):
    """A chat model that writes a fixed deliverable and passes every review.

    Two behaviours, chosen by what is asked of it. Bound to tools it answers
    with a ``write_file`` call, then acknowledges the result — the shape a
    specialist's inner loop expects. Asked for structured output it returns a
    passing :class:`ReviewVerdict`, which is what the QA reviewer needs to let a
    stage advance to its gate.
    """

    @property
    def _llm_type(self) -> str:
        """Name the model type for LangChain's own bookkeeping.

        Returns:
            The provider name.
        """
        return PROVIDER_NAME

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Answer one turn of a specialist's loop.

        Args:
            messages: The conversation so far.
            stop: Unused; the scripted model has no sampling to stop.
            run_manager: Unused callback manager.
            **kwargs: Unused provider options.

        Returns:
            A ``write_file`` tool call, or a plain acknowledgement once the write
            has come back.
        """
        if messages and isinstance(messages[-1], ToolMessage):
            return _result(AIMessage(content="Saved the deliverable."))
        path = _deliverable_path(messages)
        stage = path.rsplit("/", 1)[-1].removesuffix(".md").replace("-", " ").title()
        return _result(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_file",
                        "args": {
                            "path": path,
                            "content": _DELIVERABLE_BODY.format(stage=stage),
                        },
                        "id": "call_scripted_write",
                    }
                ],
            )
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Answer one turn on the async path the pipeline actually uses.

        The graph awaits every model call so a cancelled run aborts mid-flight
        (ADR-0009), so a model implementing only the sync path raises
        ``NotImplementedError`` the moment a real run starts.

        Args:
            messages: The conversation so far.
            stop: Unused; the scripted model has no sampling to stop.
            run_manager: Unused callback manager.
            **kwargs: Unused provider options.

        Returns:
            The same answer the sync path gives.
        """
        return self._generate(messages, stop, None, **kwargs)

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[Any, Any]:
        """Accept the specialist's tools and answer as though bound to them.

        A specialist binds its tools before it invokes anything, so a model that
        does not implement this raises ``NotImplementedError`` before a single
        stage can run. The tools themselves are ignored: this model always
        answers with the one ``write_file`` call the pipeline needs.

        Args:
            tools: The tools the specialist offers; ignored.
            **kwargs: Unused binding options.

        Returns:
            This model, unchanged.
        """
        return self

    def with_structured_output(self, schema: Any = None, **kwargs: Any) -> Runnable[Any, Any]:
        """Return a runnable answering the QA reviewer with a passing verdict.

        Args:
            schema: The structure the caller wants; only ``ReviewVerdict`` is
                served, since that is the one structured call the pipeline makes.
            **kwargs: Unused structured-output options.

        Returns:
            A runnable producing a passing verdict.
        """
        return RunnableLambda(
            lambda _: ReviewVerdict(
                passed=True,
                summary="Scripted reviewer passes every deliverable.",
                discrepancies=[],
            )
        )


def _result(message: AIMessage) -> ChatResult:
    """Wrap one message as a chat result.

    Args:
        message: The message to return.

    Returns:
        The single-generation chat result.
    """
    return ChatResult(generations=[ChatGeneration(message=message)])


def build_scripted_model() -> BaseChatModel:
    """Build the scripted model, refusing unless it was explicitly allowed.

    Returns:
        The scripted chat model.

    Raises:
        ConfigError: Unless ``MARKETING_OS_ALLOW_SCRIPTED_MODEL=1``. A provider
            that fabricates deliverables must never be reachable by accident, so
            selecting it takes two deliberate settings rather than one.
    """
    if os.environ.get(ENABLE_FLAG) != "1":
        raise ConfigError(
            f"The '{PROVIDER_NAME}' provider writes fabricated deliverables and is "
            f"for testing only. Set {ENABLE_FLAG}=1 if that is genuinely what you want."
        )
    return ScriptedChatModel()
