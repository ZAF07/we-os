"""CLI tests for ``marketing_os.entrypoints.cli``.

The CLI is administrative: it provisions the database and publishes the
onboarding question set, and it does not run campaigns (ADR-0026). These tests
cover argument registration, question-set file validation, and the settings
error every command is guarded by.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from marketing_os.entrypoints.cli import build_parser, main
from marketing_os.errors import ConfigError


def test_only_the_administrative_commands_are_registered(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A campaign runs one way — through the API — so the CLI offers no way to
    # start one (ADR-0026).
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    usage = capsys.readouterr().out
    assert "{init-db,publish-questionnaire}" in usage
    for gone in ("new-campaign", "check", "agents"):
        assert gone not in usage


def test_config_error_when_root_missing_claude_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Settings are resolved before any command runs, so a misconfigured root is
    # reported rather than surfacing as a failure deep inside provisioning.
    monkeypatch.setenv("MARKETING_OS_ROOT", str(tmp_path))
    code = main(["init-db", "--dsn", "postgresql://x"])
    err = capsys.readouterr().err
    assert code == 1
    assert "Config error" in err


def test_publish_questionnaire_is_registered_with_its_dsn_and_file() -> None:
    args = build_parser().parse_args(
        ["publish-questionnaire", "--dsn", "postgresql://x", "--file", "set.json"]
    )
    assert args.dsn == "postgresql://x"
    assert args.file == "set.json"


def test_init_db_is_registered_with_its_dsn_and_app_role() -> None:
    args = build_parser().parse_args(
        ["init-db", "--dsn", "postgresql://admin@x", "--app-role", "marketing_os_app"]
    )
    assert args.dsn == "postgresql://admin@x"
    assert args.app_role == "marketing_os_app"


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
