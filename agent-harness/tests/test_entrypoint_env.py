"""Tests for ``.env`` auto-loading at process startup.

``load_env`` resolves ``.env`` from the current working directory, so each test
changes into a temporary directory and asserts the precedence rules: a local
``.env`` is picked up, a value already in the environment is never overridden,
and a missing ``.env`` is a silent no-op.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from marketing_os.entrypoints.env import load_env


def test_load_env_reads_local_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("MARKETING_OS_TAVILY_API_KEY=tvly-from-dotenv\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MARKETING_OS_TAVILY_API_KEY", raising=False)

    load_env()

    assert os.environ["MARKETING_OS_TAVILY_API_KEY"] == "tvly-from-dotenv"


def test_load_env_does_not_override_existing_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("MARKETING_OS_TAVILY_API_KEY=tvly-from-dotenv\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MARKETING_OS_TAVILY_API_KEY", "tvly-from-real-env")

    load_env()

    assert os.environ["MARKETING_OS_TAVILY_API_KEY"] == "tvly-from-real-env"


def test_load_env_is_a_noop_when_dotenv_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MARKETING_OS_TAVILY_API_KEY", raising=False)

    load_env()

    assert "MARKETING_OS_TAVILY_API_KEY" not in os.environ
