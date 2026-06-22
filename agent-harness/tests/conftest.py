"""Shared test fixtures: a hermetic temp Marketing OS repo + Settings.

No network and no LLM are needed for the offline suite — we test the gate, the
schemas, the per-agent config/tool wiring, the guardrails, the real browser tool
(local file:// pages), and the ADK graph assembly (agents construct without a
live model call).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from marketing_os.config import Settings

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
- **Competitors:** BigBox Fitness
"""

_GOAL_FILLED = """\
# Campaign Goal — Acme Spring

## Required
- **Customer:** acme
- **Primary business objective:** +40 new memberships in 8 weeks

### Success metrics (define all three tiers)
- **Business KPI:** 40 memberships
- **Marketing KPI:** 3% landing-page conversion
- **Creative KPI:** 25% hook rate

## Optional
- **Offer / promotion:** First month half price
"""

_RULES = "# Operating Principles\n\n1. Strategy before content.\n2. Explain why; tie to the objective.\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal Marketing OS repo with a complete DNA + goal for customer 'acme'."""
    _write(tmp_path / ".claude" / "rules" / "operating-principles.md", _RULES)
    _write(tmp_path / "templates" / "customer-dna.md", _DNA_TEMPLATE)
    _write(tmp_path / "templates" / "campaign-goal.md", _GOAL_TEMPLATE)
    _write(tmp_path / "customers" / "acme" / "dna.md", _DNA_FILLED)
    _write(tmp_path / "campaigns" / "acme" / "goal.md", _GOAL_FILLED)
    _write(tmp_path / "guardrails" / "shared.md", "- Grounded in the DNA.\n- Explain why.\n")
    _write(tmp_path / "guardrails" / "strategy.md", "- Positioning is distinct and defensible.\n")
    return tmp_path


@pytest.fixture
def settings(repo: Path) -> Settings:
    """Settings rooted at the temp repo (uses the packaged agents.yaml + prompts)."""
    s = Settings(root=repo)
    s.validate_root()
    return s
