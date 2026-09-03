"""CLI tests for ``marketing_os.entrypoints.cli``.

These drive ``main()`` end to end with a scripted chat model and a fake reviewer
(injected into the runner's graph builders), so command invocation, exit codes,
and error rendering are exercised with no network. The CLI resolves its own
settings from ``MARKETING_OS_ROOT``, which is pointed at the hermetic repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import (
    FAIL_VERDICT,
    PLACEHOLDER_DNA,
    SLUG,
    TENANT,
    install_scripted_graph,
    run_without_approval_gates,
    write_all_agent_specs,
)
from marketing_os.config import Settings
from marketing_os.entrypoints.cli import main
from marketing_os.errors import ConfigError


@pytest.fixture
def cli(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the CLI at the hermetic repo and inject the scripted graph.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_TENANT_ID", TENANT)
    install_scripted_graph(monkeypatch)


def test_check_passes_on_valid_repo(cli: None, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["check", "acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Stage 0 gate passed" in out
    assert "acme" in out


def test_check_fails_on_placeholder_dna(
    cli: None, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "tenants" / TENANT / "dna.md").write_text(PLACEHOLDER_DNA, encoding="utf-8")
    code = main(["check", "acme"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Stage 0 gate FAILED" in out
    assert "    - " in out


def test_agents_lists_specialists_and_tools(cli: None, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["agents"])
    out = capsys.readouterr().out
    assert code == 0
    assert "market-research" in out
    assert "WebSearch" in out


def test_new_campaign_single_stage_writes_deliverable(
    cli: None, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["new-campaign", "acme", "--stage", "research"])
    out = capsys.readouterr().out
    assert code == 0
    assert (repo / "tenants" / TENANT / "campaigns" / SLUG / "research.md").is_file()
    assert "Stage 0 gate passed" in out
    assert "complete" in out
    assert "research:" in out


def test_new_campaign_full_pipeline_runs_every_stage(
    cli: None, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_without_approval_gates(monkeypatch)
    write_all_agent_specs(Settings(root=repo))
    code = main(["new-campaign", "acme"])
    out = capsys.readouterr().out
    assert code == 0
    for name in ("research.md", "brand-strategy.md", "performance-plan.md"):
        assert (repo / "tenants" / TENANT / "campaigns" / SLUG / name).is_file()
    assert "Stages run: 6" in out


def test_new_campaign_slug_override_targets_named_campaign(
    cli: None, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "tenants" / TENANT / "campaigns" / "spring" / "goal.md").parent.mkdir(
        parents=True, exist_ok=True
    )
    (repo / "tenants" / TENANT / "campaigns" / "spring" / "goal.md").write_text(
        (repo / "tenants" / TENANT / "campaigns" / SLUG / "goal.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    code = main(["new-campaign", "spring", "--stage", "research"])
    assert code == 0
    capsys.readouterr()
    assert (repo / "tenants" / TENANT / "campaigns" / "spring" / "research.md").is_file()


def test_new_campaign_halts_when_gate_fails(
    cli: None, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "tenants" / TENANT / "dna.md").write_text(PLACEHOLDER_DNA, encoding="utf-8")
    code = main(["new-campaign", "acme", "--stage", "research"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Stage 0 gate FAILED" in out
    assert not (repo / "tenants" / TENANT / "campaigns" / SLUG / "research.md").is_file()


def test_new_campaign_provider_override_is_applied(
    cli: None, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[str] = []
    import marketing_os.graph.runner as runner_mod

    original = runner_mod.run_campaign

    def spy(settings: Settings, *args: object, **kwargs: object) -> object:
        seen.append(settings.provider)
        return original(settings, *args, **kwargs)

    monkeypatch.setattr(runner_mod, "run_campaign", spy)
    code = main(["new-campaign", "acme", "--stage", "research", "--provider", "anthropic"])
    capsys.readouterr()
    assert code == 0
    assert seen == ["anthropic"]


def test_run_failure_renders_error_and_discrepancies(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_MAX_QA", "1")
    monkeypatch.setenv("MARKETING_OS_TENANT_ID", TENANT)
    install_scripted_graph(monkeypatch, verdicts=[FAIL_VERDICT])
    code = main(["new-campaign", "acme", "--stage", "research"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Error:" in captured.err
    assert "failed QA" in captured.err


def test_config_error_when_root_missing_claude_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(tmp_path))
    code = main(["check", "acme"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Config error" in err


def test_publish_questionnaire_is_registered_with_its_dsn_and_file(cli: None) -> None:
    from marketing_os.entrypoints.cli import build_parser

    args = build_parser().parse_args(
        ["publish-questionnaire", "--dsn", "postgresql://x", "--file", "set.json"]
    )
    assert args.dsn == "postgresql://x"
    assert args.file == "set.json"


def test_a_question_set_file_round_trips(tmp_path: Path) -> None:
    from marketing_os.entrypoints.cli import load_questionnaire_file
    from marketing_os.questionnaire import SEED_QUESTIONNAIRE

    path = tmp_path / "questions.json"
    path.write_text(SEED_QUESTIONNAIRE.model_dump_json(), encoding="utf-8")
    loaded = load_questionnaire_file(path)
    assert loaded.version == SEED_QUESTIONNAIRE.version
    assert [q.id for q in loaded.questions] == [q.id for q in SEED_QUESTIONNAIRE.questions]


def test_a_malformed_question_set_is_refused_before_it_reaches_a_business(
    tmp_path: Path,
) -> None:
    from marketing_os.entrypoints.cli import load_questionnaire_file

    path = tmp_path / "questions.json"
    path.write_text('{"version": 2, "published_at": "x", "questions": [{"id": "q"}]}', "utf-8")
    with pytest.raises(ConfigError):
        load_questionnaire_file(path)


def test_an_absent_question_set_file_is_refused(tmp_path: Path) -> None:
    from marketing_os.entrypoints.cli import load_questionnaire_file

    with pytest.raises(ConfigError):
        load_questionnaire_file(tmp_path / "nope.json")


def test_new_campaign_reports_a_run_waiting_on_approval(
    cli: None, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_all_agent_specs(Settings(root=repo))
    code = main(["new-campaign", "acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "waiting for your approval of 'brand-strategy'" in out
    assert "complete" not in out
