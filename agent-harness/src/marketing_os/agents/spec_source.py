"""Resolve the :class:`AgentSpec` for any pipeline agent behind one seam.

Two sources answer for a spec, hidden behind :class:`SpecSource` so callers never
branch on which one did: the five specialists are defined as markdown under
``.claude/agents/`` (:func:`load_agent`), and the Marketing Director is defined
inline here — it owns the campaign-strategy stage but has no agent file, so its
spec and system-prompt body live together in this module rather than being
hand-assembled at the graph-wiring site.
"""

from __future__ import annotations

from marketing_os.agents.loader import AgentSpec, load_agent
from marketing_os.config import Settings
from marketing_os.governance.pipeline import DIRECTOR

DIRECTOR_BODY = """\
You are the **Marketing Director** in the Marketing OS specialist hierarchy — the
orchestrator. You own the business goal, campaign strategy, budget allocation, and
KPI planning. You NEVER produce creative assets or generation prompts.

## Your single output
A campaign strategy: the approach, channels-at-a-glance, budget allocation, and the
three KPI tiers (Business / Marketing / Creative), each tied to the business
objective.

## Guardrails (non-negotiable)
- Ground everything in the Customer DNA and the approved brand strategy. Never invent
  what the DNA omits — say so instead.
- Strategy before content: do not specify creative or assets.
- Every decision explains its 'why' and ties back to the business KPI.
- Define all three KPI tiers before recommending spend.
"""


def director_spec() -> AgentSpec:
    """Return the inline specialist definition for the Director-owned stage.

    Returns:
        The :class:`AgentSpec` for the campaign-strategy stage, which has no file
        under ``.claude/agents/`` because the Director owns it directly.
    """
    return AgentSpec(
        name=DIRECTOR,
        description="Marketing Director — campaign strategy, budget, KPIs.",
        tools=["Read", "Grep", "Glob", "Write"],
        body=DIRECTOR_BODY,
    )


class SpecSource:
    """Resolves the :class:`AgentSpec` for a pipeline agent by name.

    Hides whether a spec is loaded from a ``.claude/agents/`` markdown file or is
    the inline Director definition, so the graph wiring asks for a spec by agent
    name and never special-cases the Director.
    """

    def __init__(self, settings: Settings) -> None:
        """Store the settings used to locate agent markdown files.

        Args:
            settings: The harness settings (for the agents directory).
        """
        self._settings = settings

    def spec_for(self, agent_name: str) -> AgentSpec:
        """Return the spec for an agent, from its file or the inline Director.

        Args:
            agent_name: The stage's agent name, or the Director sentinel.

        Returns:
            The resolved :class:`AgentSpec`.

        Raises:
            ConfigError: If a non-Director agent has no markdown definition.
        """
        if agent_name == DIRECTOR:
            return director_spec()
        return load_agent(self._settings, agent_name)
