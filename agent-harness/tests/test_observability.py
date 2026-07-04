"""Observability: per-run JSONL trace, structured errors, and event logging."""

from __future__ import annotations

import json
import logging
import re

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from conftest import FakeReviewer, ProgrammableChatModel, write_call
from marketing_os.config import Settings
from marketing_os.errors import GuardrailError
from marketing_os.graph import nodes, runner
from marketing_os.graph.graph import build_single_stage_graph
from marketing_os.ports import Reviewer
from marketing_os.schemas import Discrepancy, ReviewVerdict

_FAIL = ReviewVerdict(
    passed=False,
    summary="research is too thin",
    discrepancies=[Discrepancy(rubric_point="coverage", problem="no competitors", fix="add them")],
)
_PASS = ReviewVerdict(passed=True, summary="ok")


def _writing_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write the named deliverable, then stop once the tool has run."""
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    text = "\n".join(str(m.content) for m in messages)
    path = re.findall(r"campaigns/[\w-]+/[\w-]+\.md", text)[-1]
    return write_call(path, "# Deliverable\n\nContent.")


class _CrashingReviewer:
    """A reviewer that raises a non-``MarketingOSError`` to simulate a crashed run.

    Stands in for an infrastructure failure (for example the raw Playwright error
    that killed ``coast-coffee-test-four``) escaping a graph node mid-stream.
    """

    def review(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Raise instead of returning a verdict.

        Args:
            stage_key: The stage being reviewed (unused).
            deliverable_text: The deliverable text (unused).

        Raises:
            RuntimeError: Always, to simulate an unexpected crash.
        """
        raise RuntimeError("playwright navigation exploded")


def _patch_graph(monkeypatch: pytest.MonkeyPatch, reviewer: Reviewer) -> None:
    """Force the runner to build a single-stage graph wired with fakes."""

    def fake_select(settings: Settings, stage: str | None, *, web_backend, checkpointer):
        return build_single_stage_graph(
            settings,
            stage or "research",
            model=ProgrammableChatModel(handler=_writing_handler),
            reviewer=reviewer,
        )

    monkeypatch.setattr(runner, "_select_graph", fake_select)


def test_failed_run_writes_trace_and_structured_error(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.max_qa_iterations = 0
    _patch_graph(monkeypatch, FakeReviewer([_FAIL]))

    with pytest.raises(GuardrailError) as excinfo:
        runner.run_campaign(settings, "acme", "acme", stage="research")

    exc = excinfo.value
    detail = exc.detail
    assert detail["stage"] == "research"
    assert detail["discrepancies"][0]["rubric_point"] == "coverage"
    assert exc.run_log

    traces = list((settings.logs_dir / "acme").glob("*.jsonl"))
    assert traces, "a run-log trace file should be written"
    lines = [json.loads(line) for line in traces[0].read_text().splitlines() if line]
    events = [line["event"] for line in lines]
    assert "stage.failed" in events
    assert "run.summary" in events
    failed = next(line for line in lines if line["event"] == "stage.failed")
    assert failed["discrepancies"][0]["rubric_point"] == "coverage"
    summary = next(line for line in lines if line["event"] == "run.summary")
    assert summary["outcome"] == "error"


def test_crashed_run_writes_terminal_error_event(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_graph(monkeypatch, _CrashingReviewer())

    with pytest.raises(RuntimeError, match="playwright navigation exploded"):
        runner.run_campaign(settings, "acme", "acme", stage="research")

    traces = list((settings.logs_dir / "acme").glob("*.jsonl"))
    assert traces, "a run-log trace file should be written even on crash"
    lines = [json.loads(line) for line in traces[0].read_text().splitlines() if line]
    summary = next(line for line in lines if line["event"] == "run.summary")
    assert summary["outcome"] == "error"
    assert "playwright navigation exploded" in summary["error"]["message"]


def test_crashed_run_logs_terminal_error_to_console(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_graph(monkeypatch, _CrashingReviewer())

    with (
        caplog.at_level(logging.INFO, logger="marketing_os.runner"),
        pytest.raises(RuntimeError, match="playwright navigation exploded"),
    ):
        runner.run_campaign(settings, "acme", "acme", stage="research")

    messages = [record.getMessage() for record in caplog.records]
    assert any("run.summary outcome=error" in message for message in messages)


async def test_crashed_astream_writes_terminal_error_event(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_graph(monkeypatch, _CrashingReviewer())

    with pytest.raises(RuntimeError, match="playwright navigation exploded"):
        async for _ in runner.astream_campaign(settings, "acme", "acme", stage="research"):
            pass

    traces = list((settings.logs_dir / "acme").glob("*.jsonl"))
    assert traces, "a run-log trace file should be written even on crash"
    lines = [json.loads(line) for line in traces[0].read_text().splitlines() if line]
    summary = next(line for line in lines if line["event"] == "run.summary")
    assert summary["outcome"] == "error"
    assert "playwright navigation exploded" in summary["error"]["message"]


def test_run_logs_can_be_disabled(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    settings.run_logs = False
    _patch_graph(monkeypatch, FakeReviewer([_PASS]))
    result = runner.run_campaign(settings, "acme", "acme", stage="research")
    assert result.run_log is None
    assert not (settings.logs_dir / "acme").exists()


def test_stage_log_lines_carry_slug(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_graph(monkeypatch, FakeReviewer([_PASS]))

    with caplog.at_level(logging.INFO, logger="marketing_os.graph"):
        runner.run_campaign(settings, "acme", "acme", stage="research")

    stage_lines = [
        record.getMessage() for record in caplog.records if record.getMessage().startswith("stage.")
    ]
    assert stage_lines, "the run should emit stage.* log lines"
    assert all("slug=acme" in line for line in stage_lines)


def test_emit_logs_events(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="marketing_os.graph"):
        nodes._emit(
            "stage.review", stage="research", passed=False, discrepancies=[{"rubric_point": "x"}]
        )
    messages = [record.getMessage() for record in caplog.records]
    assert any("stage.review" in message for message in messages)
    assert any("rubric_point" in message or "[x]" in message for message in messages)
