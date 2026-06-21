"""Specialist loading + execution."""

from __future__ import annotations

from .loader import AgentSpec, load_agent, load_agent_file, load_all_agents
from .specialist import Specialist, compose_system

__all__ = [
    "AgentSpec",
    "load_agent",
    "load_agent_file",
    "load_all_agents",
    "Specialist",
    "compose_system",
]
