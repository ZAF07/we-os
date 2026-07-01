"""Model adapter: the reviewer runs non-thinking so structured output works."""

from __future__ import annotations

import pytest

from marketing_os.adapters.models import get_model
from marketing_os.config import Settings


def test_reviewer_model_disables_thinking(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    model = get_model(settings, role="reviewer", thinking=False)
    assert getattr(model, "extra_body", None) == {"thinking": {"type": "disabled"}}


def test_specialist_model_keeps_thinking_default(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    model = get_model(settings)
    assert not getattr(model, "extra_body", None)
