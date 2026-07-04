"""HTTP API tests for ``marketing_os.entrypoints.api.app``.

These exercise every endpoint through FastAPI's ``TestClient`` with a scripted
chat model and fake reviewer injected into the runner's graph builders, so gate,
run, SSE stream, deliverables, and run-trace endpoints are covered with no
network. The app resolves settings from ``MARKETING_OS_ROOT`` (the hermetic repo)
through an ``lru_cache`` that each test clears.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import FAIL_VERDICT, PLACEHOLDER_DNA, BlockingChatModel, install_scripted_graph


def _make_client(repo: Path) -> TestClient:
    """Build a TestClient bound to the hermetic repo with caches cleared.

    Args:
        repo: The hermetic repository root fixture.

    Returns:
        A configured (not yet entered) FastAPI test client.
    """
    from marketing_os.entrypoints.api.app import app, get_registry, get_settings

    get_settings.cache_clear()
    get_registry.cache_clear()
    return TestClient(app)


def _wait_for_status(client: TestClient, run_id: str, target: str) -> dict:
    """Poll a run's status until it reaches ``target`` or time out.

    The background run executes on the test client's portal event loop, so each
    poll (and the sleeps between them) lets the loop advance the run.

    Args:
        client: The entered test client.
        run_id: The run id to poll.
        target: The status to wait for.

    Returns:
        The status payload once it matches ``target``.
    """
    for _ in range(200):
        response = client.get(f"/runs/{run_id}")
        if response.status_code == 200 and response.json()["status"] == target:
            return response.json()
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached status {target!r}")


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
    from marketing_os.entrypoints.api.app import get_registry, get_settings

    with _make_client(repo) as entered:
        yield entered
    get_settings.cache_clear()
    get_registry.cache_clear()


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


def test_run_starts_background_job_and_returns_run_id(client: TestClient, repo: Path) -> None:
    run = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
    assert run.status_code == 202
    started = run.json()
    assert started["slug"] == "acme"
    assert started["status"] == "running"
    run_id = started["run_id"]
    assert run_id

    completed = _wait_for_status(client, run_id, "completed")
    assert completed["run_id"] == run_id
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


def test_run_background_job_fails_on_guardrail_failure(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_MAX_QA", "1")
    install_scripted_graph(monkeypatch, verdicts=[FAIL_VERDICT])
    from marketing_os.entrypoints.api.app import get_registry, get_settings

    with _make_client(repo) as client:
        started = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
        assert started.status_code == 202
        run_id = started.json()["run_id"]

        failed = _wait_for_status(client, run_id, "failed")
        assert failed["status"] == "failed"
        trace = client.get(f"/campaigns/acme/runs/{run_id}").json()["events"]

    get_settings.cache_clear()
    get_registry.cache_clear()
    summary = [event for event in trace if event.get("event") == "run.summary"][-1]
    assert summary["outcome"] == "error"
    assert summary["error"]["type"] == "guardrail"


def test_runs_endpoints_list_and_return_trace(client: TestClient) -> None:
    empty = client.get("/campaigns/acme/runs")
    assert empty.status_code == 200
    assert empty.json()["runs"] == []

    started = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
    run_id = started.json()["run_id"]
    _wait_for_status(client, run_id, "completed")

    listing = client.get("/campaigns/acme/runs")
    runs = listing.json()["runs"]
    assert runs == [run_id]

    trace = client.get(f"/campaigns/acme/runs/{run_id}")
    assert trace.status_code == 200
    events = trace.json()["events"]
    assert events
    assert any(event.get("event") == "run.summary" for event in events)


def test_get_run_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/campaigns/acme/runs/does-not-exist")
    assert response.status_code == 404


def _run_to_completion(client: TestClient, slug: str = "acme") -> str:
    """Start a background run and return its id once it has completed.

    Args:
        client: The entered test client.
        slug: The campaign slug to run.

    Returns:
        The completed run's id.
    """
    started = client.post(f"/campaigns/{slug}/run", json={"customer": "acme", "stage": "research"})
    assert started.status_code == 202
    run_id = started.json()["run_id"]
    _wait_for_status(client, run_id, "completed")
    return run_id


def _sse_events(text: str) -> list[dict]:
    """Parse the events out of an SSE response body.

    Args:
        text: The raw ``text/event-stream`` response body.

    Returns:
        The decoded event payloads, in order.
    """
    return [
        json.loads(line[len("data: ") :]) for line in text.splitlines() if line.startswith("data: ")
    ]


def test_stream_attaches_to_finished_run_replays_trace_and_closes(
    client: TestClient, repo: Path
) -> None:
    run_id = _run_to_completion(client)

    response = client.get(f"/runs/{run_id}/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)
    assert events, "the finished run's trace should be replayed"
    assert events[-1]["event"] == "run.summary", "the stream closes on the terminal summary"
    assert events[-1]["outcome"] == "ok"


def test_stream_attach_does_not_start_a_new_run(client: TestClient) -> None:
    run_id = _run_to_completion(client)
    before = client.get("/campaigns/acme/runs").json()["runs"]

    response = client.get(f"/runs/{run_id}/stream")
    assert response.status_code == 200
    _sse_events(response.text)

    assert client.get("/runs").json()["runs"] == [], "observing must not register a run"
    assert client.get("/campaigns/acme/runs").json()["runs"] == before, "no new trace is written"


def test_stream_attach_404_for_unknown_run(client: TestClient) -> None:
    assert client.get("/runs/does-not-exist/stream").status_code == 404


def test_multiple_observers_each_get_the_full_event_sequence(client: TestClient) -> None:
    run_id = _run_to_completion(client)

    first = _sse_events(client.get(f"/runs/{run_id}/stream").text)
    second = _sse_events(client.get(f"/runs/{run_id}/stream").text)

    assert first == second
    assert first[-1]["event"] == "run.summary"


def _install_blocking_client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Build a client whose runs block in-flight until cancelled.

    Each background run builds a fresh :class:`BlockingChatModel`, so a run stays
    active in the registry — held inside the specialist's awaited LLM call — until
    it is cancelled. Lets concurrency, cancellation, and listing be observed at the
    HTTP layer.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Returns:
        A configured (not yet entered) test client backed by blocking runs.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    install_scripted_graph(monkeypatch, model_factory=BlockingChatModel)
    return _make_client(repo)


def test_second_run_same_slug_conflicts_while_cross_slug_is_concurrent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "campaigns" / "beta").mkdir(parents=True, exist_ok=True)
    (repo / "campaigns" / "beta" / "goal.md").write_text(
        (repo / "campaigns" / "acme" / "goal.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    from marketing_os.entrypoints.api.app import get_registry, get_settings

    with _install_blocking_client(repo, monkeypatch) as client:
        first = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
        assert first.status_code == 202
        first_id = first.json()["run_id"]
        _wait_for_status(client, first_id, "running")

        conflict = client.post(
            "/campaigns/acme/run", json={"customer": "acme", "stage": "research"}
        )
        assert conflict.status_code == 409
        detail = conflict.json()["detail"]
        assert detail["type"] == "slug_busy"
        assert detail["active_run_id"] == first_id

        cross = client.post("/campaigns/beta/run", json={"customer": "acme", "stage": "research"})
        assert cross.status_code == 202

        active_slugs = {run["slug"] for run in client.get("/runs").json()["runs"]}
        assert active_slugs == {"acme", "beta"}

        for run_id in (first_id, cross.json()["run_id"]):
            assert client.post(f"/runs/{run_id}/cancel").status_code == 200

    get_settings.cache_clear()
    get_registry.cache_clear()


def test_cancel_endpoint_stops_run_and_marks_it_cancelled(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from marketing_os.entrypoints.api.app import get_registry, get_settings

    with _install_blocking_client(repo, monkeypatch) as client:
        started = client.post("/campaigns/acme/run", json={"customer": "acme", "stage": "research"})
        assert started.status_code == 202
        run_id = started.json()["run_id"]
        assert _wait_for_status(client, run_id, "running")["status"] == "running"

        cancel = client.post(f"/runs/{run_id}/cancel")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        assert client.get("/runs").json()["runs"] == []
        assert client.get(f"/runs/{run_id}").json()["status"] == "cancelled"

    get_settings.cache_clear()
    get_registry.cache_clear()


def test_get_run_status_404_for_unknown_run(client: TestClient) -> None:
    assert client.get("/runs/does-not-exist").status_code == 404


def test_cancel_404_for_unknown_run(client: TestClient) -> None:
    assert client.post("/runs/does-not-exist/cancel").status_code == 404


def test_get_run_status_infers_interrupted_from_orphaned_trace(
    client: TestClient, repo: Path
) -> None:
    run_id = "20260704T120000Z-deadbeef"
    trace = repo / "logs" / "acme" / f"{run_id}.jsonl"
    trace.parent.mkdir(parents=True, exist_ok=True)
    trace.write_text('{"event": "stage.start", "stage": "research"}\n', encoding="utf-8")

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interrupted"
    assert body["slug"] == "acme"
