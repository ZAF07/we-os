"""Specialist loading and construction."""

from __future__ import annotations

from marketing_os.agents.loader import AgentSpec, load_agent, load_agent_file, load_all_agents
from marketing_os.agents.specialist import DIRECTOR_BODY, build_specialist, compose_system

__all__ = [
    "AgentSpec",
    "load_agent",
    "load_agent_file",
    "load_all_agents",
    "build_specialist",
    "compose_system",
    "DIRECTOR_BODY",
]
