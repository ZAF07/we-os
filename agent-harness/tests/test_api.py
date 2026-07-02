"""HTTP API tests for ``marketing_os.entrypoints.api.app``.

These exercise every endpoint through FastAPI's ``TestClient`` with a scripted
chat model and fake reviewer injected into the runner's graph builders, so gate,
run, SSE stream, deliverables, and run-trace endpoints are covered with no
network. The app resolves settings from ``MARKETING_OS_ROOT`` (the hermetic repo)
through an ``lru_cache`` that each test clears.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import FAIL_VERDICT, PLACEHOLDER_DNA, install_scripted_graph


def _make_client(repo: Path) -> TestClient:
    """Build a TestClient bound to the hermetic repo with caches cleared.

    Args:
        repo: The hermetic repository root fixture.

    Returns:
        A configured (not yet entered) FastAPI test client.
    """
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    return TestClient(app)


@pytest.fixture
def client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a hermetic API client with the scripted graph installed.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch)
    from marketing_os.entrypoints.api.app import get_settings

    with _make_client(repo) as entered:
        yield entered
    get_settings.cache_clear()


def test_health_reports_provider_and_root(client: TestClient, repo: Path) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["root"] == str(repo)
    assert body["provider"]


def test_create_campaign_scaffolds_goal_from_template(client: TestClient, repo: Path) -> None:
    response = client.post("/campaigns", json={"customer": "acme", "slug": "newcamp"})
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "newcamp"
    assert body["goal_created_from_template"] is True
    assert (repo / "campaigns" / "newcamp" / "goal.md").is_file()
    assert body["gate_ok"] is False
    assert body["gate_issues"]


def test_create_campaign_is_idempotent_when_goal_exists(client: TestClient) -> None:
    response = client.post("/campaigns", json={"customer": "acme"})
    assert response.status_code == 200
    body = response.json()
    assert body["goal_created_from_template"] is False
    assert body["gate_ok"] is True


def test_create_campaign_500_when_template_missing(client: TestClient, repo: Path) -> None:
    (repo / "templates" / "campaign-goal.md").unlink()
    response = client.post("/campaigns", json={"customer": "acme", "slug": "notmpl"})
    assert response.status_code == 500
    assert "template missing" in response.json()["detail"]


def test_gate_endpoint_reports_pass(client: TestClient) -> None:
    response = client.get("/campaigns/acme/gate", params={"customer": "acme"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["issues"] == []


def test_gate_endpoint_reports_failure(client: TestClient, repo: Path) -> None:
    (repo / "customers" / "acme" / "dna.md").write_text(PLACEHOLDER_DNA, encoding="utf-8")
    response = client.get("/campaigns/acme/gate", params={"customer": "acme"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["issues"]


def test_deliverables_404_when_campaign_missing(client: TestClient) -> None:
    response = client.get("/campaigns/ghost/deliverables")
    assert response.status_code == 404


def test_run_then_deliverables_lists_written_files(client: TestClient, repo: Path) -> None:
    run = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
    assert run.status_code == 200
    result = run.json()
    assert result["slug"] == "acme"
    assert [stage["stage"] for stage in result["stages"]] == ["research"]
    assert (repo / "campaigns" / "acme" / "research.md").is_file()

    listing = client.get("/campaigns/acme/deliverables")
    assert listing.status_code == 200
    names = [entry["name"] for entry in listing.json()["files"]]
    assert "research.md" in names
    assert "goal.md" in names


def test_run_returns_409_when_gate_fails(client: TestClient, repo: Path) -> None:
    (repo / "customers" / "acme" / "dna.md").write_text(PLACEHOLDER_DNA, encoding="utf-8")
    response = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
    assert response.status_code == 409
    assert response.json()["detail"]["type"] == "gate"


def test_run_returns_422_on_guardrail_failure(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_MAX_QA", "1")
    install_scripted_graph(monkeypatch, verdicts=[FAIL_VERDICT])
    from marketing_os.entrypoints.api.app import get_settings

    with _make_client(repo) as client:
        response = client.post(
            "/campaigns/acme/run", json={"customer": "acme", "stage": "research"}
        )
    get_settings.cache_clear()
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["type"] == "guardrail"
    assert "failed QA" in detail["message"]


def test_runs_endpoints_list_and_return_trace(client: TestClient) -> None:
    empty = client.get("/campaigns/acme/runs")
    assert empty.status_code == 200
    assert empty.json()["runs"] == []

    client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})

    listing = client.get("/campaigns/acme/runs")
    runs = listing.json()["runs"]
    assert len(runs) == 1

    trace = client.get(f"/campaigns/acme/runs/{runs[0]}")
    assert trace.status_code == 200
    events = trace.json()["events"]
    assert events
    assert any(event.get("event") == "run.summary" for event in events)


def test_get_run_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/campaigns/acme/runs/does-not-exist")
    assert response.status_code == 404


def test_stream_emits_sse_progress_and_done(client: TestClient, repo: Path) -> None:
    response = client.get(
        "/campaigns/acme/stream", params={"customer": "acme", "stage": "research"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [line for line in response.text.splitlines() if line.startswith("data: ")]
    assert frames
    assert '"campaign.done"' in response.text
    assert (repo / "campaigns" / "acme" / "research.md").is_file()
