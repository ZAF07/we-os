"""Shared test fixtures: scripted fakes and a hermetic temp repo."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from marketing_os.config import Settings
from marketing_os.schemas import ReviewVerdict

Handler = Callable[[list[BaseMessage], int], AIMessage]


class ProgrammableChatModel(BaseChatModel):
    """A scripted chat model whose replies are produced by a handler callable.

    The handler receives the current message list and the zero-based index of the
    model call, so a test can make the model write a deliverable, refuse to, or
    revise based on the conversation so far. No network is used.
    """

    handler: Handler
    calls: list[int] = Field(default_factory=list)
    model_config = {"arbitrary_types_allowed": True}

    @property
    def _llm_type(self) -> str:
        """Return the model type identifier."""
        return "programmable"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ProgrammableChatModel:
        """Ignore tool binding and return self, since replies are scripted.

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
        """Produce the next scripted reply.

        Args:
            messages: The conversation so far.
            stop: Stop sequences (ignored).
            run_manager: The callback manager (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            A chat result wrapping the handler's message.
        """
        index = len(self.calls)
        self.calls.append(1)
        message = self.handler(list(messages), index)
        return ChatResult(generations=[ChatGeneration(message=message)])


def write_call(path: str, content: str, call_id: str = "call_write") -> AIMessage:
    """Build an assistant message that calls the ``write_file`` tool.

    Args:
        path: The deliverable path to write.
        content: The deliverable content.
        call_id: The tool-call id.

    Returns:
        An ``AIMessage`` carrying a single ``write_file`` tool call.
    """
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "write_file", "args": {"path": path, "content": content}, "id": call_id}
        ],
    )


def read_call(path: str, call_id: str = "call_read") -> AIMessage:
    """Build an assistant message that calls the ``read_file`` tool.

    Args:
        path: The path to read.
        call_id: The tool-call id.

    Returns:
        An ``AIMessage`` carrying a single ``read_file`` tool call.
    """
    return AIMessage(
        content="",
        tool_calls=[{"name": "read_file", "args": {"path": path}, "id": call_id}],
    )


class FakeReviewer:
    """A reviewer that returns a scripted sequence of verdicts.

    The final verdict repeats once the script is exhausted so revise loops that
    eventually pass are easy to express.
    """

    def __init__(self, verdicts: list[ReviewVerdict]) -> None:
        """Initialise the fake reviewer.

        Args:
            verdicts: The verdicts to return in order.
        """
        self._verdicts = list(verdicts)
        self.calls: list[tuple[str, str]] = []

    def review(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Return the next scripted verdict.

        Args:
            stage_key: The stage being reviewed.
            deliverable_text: The deliverable text (recorded for assertions).

        Returns:
            The next scripted verdict, or the last one once exhausted.
        """
        self.calls.append((stage_key, deliverable_text))
        if len(self._verdicts) > 1:
            return self._verdicts.pop(0)
        return self._verdicts[0]


_DNA_TEMPLATE = """\
# Customer DNA — <CUSTOMER NAME>

## Required (the agent will not start without these)

### Business
- **Business name:** <name>
- **What they sell:** <products/services>

### Customers
- **Primary segment(s):** <who buys>

### Differentiation
- **Why customers choose them over alternatives:** <reason>

## Recommended

- **Competitors:** <who>
"""

_GOAL_TEMPLATE = """\
# Campaign Goal — <CAMPAIGN NAME>

## Required

- **Customer:** <name>
- **Primary business objective:** <outcome>

### Success metrics (define all three tiers)
- **Business KPI:** <target>
- **Marketing KPI:** <target>
- **Creative KPI:** <target>

## Optional

- **Offer / promotion:** <if any>
"""

_DNA_FILLED = """\
# Customer DNA — Acme

## Business
- **Business name:** Acme Climbing Gym
- **What they sell:** Monthly bouldering memberships and intro classes

## Customers
- **Primary segment(s):** Urban 22-35 beginners curious about climbing

## Differentiation
- **Why customers choose them over alternatives:** Only gym with free coached intro sessions

## Recommended
- **Competitors:** BigBox Fitness, two independent gyms
"""

_GOAL_FILLED = """\
# Campaign Goal — Acme Spring

## Required
- **Customer:** acme
- **Primary business objective:** +40 new memberships in 8 weeks

### Success metrics (define all three tiers)
- **Business KPI:** 40 memberships
- **Marketing KPI:** 3% landing-page conversion
- **Creative KPI:** 25% hook rate on intro video

## Optional
- **Offer / promotion:** First month half price
"""

_AGENT_MD = """\
---
name: market-research
description: Produces research findings only.
tools: Read, Grep, Glob, Write, WebSearch, WebFetch
---

You are the **Market Research Agent**. Output research findings only.
"""

_RULES_MD = """\
# Operating Principles

1. Strategy before content.
2. Every recommendation explains why and ties to a business objective.
"""


def _write(path: Path, text: str) -> None:
    """Write text to a path, creating parent directories.

    Args:
        path: The destination path.
        text: The content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a minimal Marketing OS repo with valid DNA and goal for 'acme'.

    Args:
        tmp_path: The pytest temporary directory.

    Returns:
        The repository root path.
    """
    _write(tmp_path / ".claude" / "agents" / "market-research.md", _AGENT_MD)
    _write(tmp_path / ".claude" / "rules" / "operating-principles.md", _RULES_MD)
    _write(tmp_path / "templates" / "customer-dna.md", _DNA_TEMPLATE)
    _write(tmp_path / "templates" / "campaign-goal.md", _GOAL_TEMPLATE)
    _write(tmp_path / "customers" / "acme" / "dna.md", _DNA_FILLED)
    _write(tmp_path / "campaigns" / "acme" / "goal.md", _GOAL_FILLED)
    _write(tmp_path / "guardrails" / "shared.md", "- DNA-grounded.\n- Explains why.\n")
    _write(tmp_path / "guardrails" / "research.md", "- Covers customer/competitor/market.\n")
    return tmp_path


@pytest.fixture
def settings(repo: Path) -> Settings:
    """Build validated settings rooted at the hermetic repo.

    Args:
        repo: The repository root fixture.

    Returns:
        The validated settings.
    """
    built = Settings(root=repo)
    built.validate_root()
    return built
