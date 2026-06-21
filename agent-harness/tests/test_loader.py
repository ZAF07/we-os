"""Agent loader: frontmatter + body + tool-grant parsing."""

from __future__ import annotations

import pytest

from marketing_os.agents import load_agent, load_all_agents
from marketing_os.agents.loader import _parse_tools, _split_frontmatter
from marketing_os.errors import ConfigError


def test_load_agent_parses_frontmatter_and_body(settings):
    spec = load_agent(settings, "market-research")
    assert spec.name == "market-research"
    assert spec.tools == ["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch"]
    assert "Market Research Agent" in spec.body
    assert "research findings only" in spec.body.lower()


def test_load_all_agents(settings):
    agents = load_all_agents(settings)
    assert "market-research" in agents


def test_parse_tools_handles_comma_string_and_list():
    assert _parse_tools("Read, Write , Grep") == ["Read", "Write", "Grep"]
    assert _parse_tools(["Read", "Write"]) == ["Read", "Write"]
    assert _parse_tools(None) == []


def test_split_frontmatter_requires_fences():
    with pytest.raises(ConfigError):
        _split_frontmatter("no frontmatter here")


def test_missing_agent_raises(settings):
    with pytest.raises(ConfigError):
        load_agent(settings, "does-not-exist")
