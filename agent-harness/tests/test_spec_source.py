"""SpecSource: one seam resolving file-defined and inline-Director specs.

Proves callers ask for a spec by agent name and never branch on origin — a
markdown specialist loads from ``.claude/agents/``, and the Director resolves to
its inline definition without a file.
"""

from __future__ import annotations

import pytest

from marketing_os.agents.spec_source import SpecSource, director_spec
from marketing_os.config import Settings
from marketing_os.errors import ConfigError
from marketing_os.governance.pipeline import DIRECTOR


def test_spec_source_loads_a_file_specialist(settings: Settings) -> None:
    spec = SpecSource(settings).spec_for("market-research")
    assert spec.name == "market-research"
    assert "Write" in spec.tools


def test_spec_source_resolves_director_inline_without_a_file(settings: Settings) -> None:
    assert not (settings.agents_dir / f"{DIRECTOR}.md").exists()
    spec = SpecSource(settings).spec_for(DIRECTOR)
    assert spec.name == DIRECTOR
    assert spec == director_spec()
    assert "Marketing Director" in spec.body


def test_spec_source_raises_for_an_unknown_file_agent(settings: Settings) -> None:
    with pytest.raises(ConfigError):
        SpecSource(settings).spec_for("no-such-agent")
