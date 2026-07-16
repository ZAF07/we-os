"""Specialist loading and construction."""

from __future__ import annotations

from marketing_os.agents.loader import AgentSpec, load_agent, load_agent_file, load_all_agents
from marketing_os.agents.spec_source import DIRECTOR_BODY, SpecSource, director_spec
from marketing_os.agents.specialist import build_specialist, compose_system

__all__ = [
    "AgentSpec",
    "load_agent",
    "load_agent_file",
    "load_all_agents",
    "build_specialist",
    "compose_system",
    "SpecSource",
    "director_spec",
    "DIRECTOR_BODY",
]
