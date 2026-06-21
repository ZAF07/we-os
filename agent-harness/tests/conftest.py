"""Shared test fixtures: a deterministic FakeProvider and a hermetic temp repo."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from marketing_os.config import Settings
from marketing_os.providers.base import Provider
from marketing_os.types import CompletionResult, Message, ToolCall, Usage


class FakeProvider(Provider):
    """Provider that replays a scripted sequence of responses (no network).

    Each script entry is a dict: {"text": str, "tools": [(name, args), ...],
    "stop_reason": str}. `tools` defaults to none; `stop_reason` defaults to
    "tool_use" if tools are present else "end_turn".
    """

    name = "fake"

    def __init__(self, scripts: list[dict]) -> None:
        self.scripts = list(scripts)
        self.calls: list[dict] = []

    def complete(self, *, system, messages, tools=None, max_tokens=16000, stream=True, on_text=None):
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        script = self.scripts.pop(0) if self.scripts else {"text": "", "stop_reason": "end_turn"}
        text = script.get("text", "")
        tool_calls = [
            ToolCall(id=f"call_{i}", name=n, arguments=a)
            for i, (n, a) in enumerate(script.get("tools", []))
        ]
        stop = script.get("stop_reason") or ("tool_use" if tool_calls else "end_turn")
        if on_text and text and stream:
            on_text(text)
        assistant = Message(
            role="assistant", content=text, tool_calls=tool_calls, provider=self.name
        )
        return CompletionResult(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop,
            usage=Usage(input_tokens=1, output_tokens=1),
            assistant_message=assistant,
        )


# ── Hermetic temp repo ──────────────────────────────────────────────────────
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal Marketing OS repo with valid DNA + goal for customer 'acme'."""
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
    s = Settings(root=repo)
    s.validate_root()
    return s
