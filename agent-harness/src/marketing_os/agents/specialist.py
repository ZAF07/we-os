"""Specialist construction — one ``create_agent`` per specialist definition.

Composes the static system prompt (governance preamble + the agent's own role and
guardrails + a DNA-grounding instruction) and builds a LangChain agent that runs
the tool-use loop. The Customer DNA text itself is injected at stage entry as part
of the task message, so the agent can be built once and reused across a run.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from marketing_os.agents.loader import AgentSpec

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


def compose_system(governance: str, agent_body: str) -> str:
    """Assemble the static system prompt a specialist runs under.

    The Customer DNA is not embedded here; it is provided in the task message so
    the agent stays cheap to build. This prompt carries the governance preamble,
    the agent's role and guardrails, and the instruction to ground every
    recommendation in the DNA supplied in the conversation.

    Args:
        governance: The assembled governance preamble.
        agent_body: The specialist's role-and-guardrails markdown body.

    Returns:
        The composed system prompt string.
    """
    return (
        f"{governance}\n\n"
        "# Grounding\n\n"
        "Ground every recommendation in the Customer DNA provided in the task "
        "message. Never invent what the DNA omits — say so instead.\n\n"
        "# Your role and guardrails\n\n"
        f"{agent_body}"
    )


def build_specialist(
    spec: AgentSpec,
    *,
    model: BaseChatModel,
    tools: list[BaseTool],
    governance: str,
) -> Runnable:
    """Build a LangChain agent for one specialist definition.

    Args:
        spec: The parsed specialist definition (name, granted tools, body).
        model: The chat model the specialist reasons with.
        tools: The tools the specialist is granted.
        governance: The assembled governance preamble for the system prompt.

    Returns:
        A compiled agent that consumes and returns a ``{"messages": [...]}`` state.
    """
    return create_agent(
        model,
        tools,
        system_prompt=compose_system(governance, spec.body),
    )
