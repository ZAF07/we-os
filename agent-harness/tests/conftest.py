"""Shared test fixtures: scripted fakes and a hermetic temp repo."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from marketing_os.config import Settings
from marketing_os.schemas import Discrepancy, ReviewVerdict

Handler = Callable[[list[BaseMessage], int], AIMessage]

PLACEHOLDER_DNA = "# Customer DNA — Acme\n\n## Business\n- **Business name:** <name>\n"

PASS_VERDICT = ReviewVerdict(passed=True, summary="ok")
FAIL_VERDICT = ReviewVerdict(
    passed=False,
    summary="needs work",
    discrepancies=[Discrepancy(rubric_point="x", problem="p", fix="f")],
)


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

    async def areview(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
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


_PIPELINE_AGENTS = {
    "brand-strategy": "You are the Brand Strategy Agent.",
    "creative-director": "You are the Creative Director Agent.",
    "creative-asset-prompt": "You are the Creative Asset Prompt Agent.",
    "performance-marketing": "You are the Performance Marketing Agent.",
}


def write_all_agent_specs(settings: Settings) -> None:
    """Write the downstream specialist specs so a full pipeline run can build.

    The ``repo`` fixture ships only ``market-research.md``; the remaining stages
    need their agent markdown present before the campaign graph can be assembled.

    Args:
        settings: The harness settings locating the agents directory.
    """
    for name, body in _PIPELINE_AGENTS.items():
        path = settings.agents_dir / f"{name}.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {name}\ntools: Read, Grep, Glob, Write\n---\n{body}",
            encoding="utf-8",
        )


def deliverable_from(messages: list[BaseMessage]) -> str:
    """Extract the ``campaigns/*.md`` deliverable path named in the seeded task.

    Args:
        messages: The conversation so far.

    Returns:
        The last ``campaigns/<slug>/<name>.md`` path found in the messages.
    """
    text = "\n".join(str(m.content) for m in messages)
    matches = re.findall(r"campaigns/[\w-]+/[\w-]+\.md", text)
    assert matches, "no deliverable path in task"
    return matches[-1]


def writing_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write the deliverable named in the task, then stop once the tool has run.

    Args:
        messages: The conversation so far.
        index: The model-call index (unused).

    Returns:
        A ``write_file`` tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    path = deliverable_from(messages)
    return write_call(path, f"# Deliverable\n\nContent for {path}.")


def install_scripted_graph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    handler: Handler = writing_handler,
    verdicts: list[ReviewVerdict] | None = None,
) -> None:
    """Patch the runner's graph builders to inject a scripted model and reviewer.

    The CLI and API entrypoints build the graph internally through the runner, so
    they never expose a model seam. This wraps :func:`build_campaign_graph` and
    :func:`build_single_stage_graph` as the runner imports them, defaulting the
    ``model`` and ``reviewer`` arguments to hermetic fakes so no network is used.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        handler: The scripted chat-model handler.
        verdicts: The reviewer verdict script; defaults to a single pass.
    """
    from marketing_os.graph import graph as graph_mod
    from marketing_os.graph import runner as runner_mod

    script = list(verdicts) if verdicts else [PASS_VERDICT]
    real_campaign = graph_mod.build_campaign_graph
    real_single = graph_mod.build_single_stage_graph

    def campaign(settings: Settings, **kwargs: Any) -> Any:
        kwargs.setdefault("model", ProgrammableChatModel(handler=handler))
        kwargs.setdefault("reviewer", FakeReviewer(list(script)))
        return real_campaign(settings, **kwargs)

    def single(settings: Settings, stage_key: str, **kwargs: Any) -> Any:
        kwargs.setdefault("model", ProgrammableChatModel(handler=handler))
        kwargs.setdefault("reviewer", FakeReviewer(list(script)))
        return real_single(settings, stage_key, **kwargs)

    monkeypatch.setattr(runner_mod, "build_campaign_graph", campaign)
    monkeypatch.setattr(runner_mod, "build_single_stage_graph", single)
