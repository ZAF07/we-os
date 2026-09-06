"""The Workspace's data contract, pinned at the engine boundary.

The Workspace is the screen where the product happens: a person reads what the
system produced and decides. It renders entirely from the engine, so what it can
show is exactly what these endpoints return — and this file drives them in the
order the screen calls them, on a real campaign that runs to a live Approval
Gate.

It exists because the browser suite cannot run on a clean checkout (it needs
Clerk credentials and a seeded engine), so without this the frontend's contract
would be asserted nowhere that actually executes. A field quietly dropped from a
payload breaks the screen; here it breaks a test first.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from conftest import (
    PLACEHOLDER_DNA,
    SLUG,
    TENANT,
    authenticate,
    clear_prototype_adapters,
    deliverable_from,
    install_prototype_adapters,
    install_scripted_graph,
    write_all_agent_specs,
    write_call,
)
from marketing_os.config import Settings


def _numbered_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write a deliverable stamped with the model call that produced it.

    Stamping the call index is what lets the version assertions tell version 2
    from version 1 without depending on the feedback text being echoed back.

    Args:
        messages: The conversation so far.
        index: Which model call this is.

    Returns:
        A ``write_file`` tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    path = deliverable_from(messages)
    return write_call(path, f"# Deliverable\n\nDraft {index} for {path}.")


def _wait_for_status(client: TestClient, run_id: str, target: str) -> dict:
    """Poll a run's status until it reaches ``target``.

    Args:
        client: The entered test client.
        run_id: The run to poll.
        target: The status to wait for.

    Returns:
        The status payload.

    Raises:
        AssertionError: If the run never reaches the status.
    """
    for _ in range(300):
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
    write_all_agent_specs(Settings(root=repo))
    install_scripted_graph(monkeypatch, handler=_numbered_handler)
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)
    with TestClient(app) as entered:
        yield entered
    get_settings.cache_clear()
    clear_prototype_adapters()


def test_workspace_first_load_carries_every_field_the_stepper_needs(
    client: TestClient,
) -> None:
    """`GET /campaigns/{slug}` — what the server component renders from."""
    campaign = client.get(f"/campaigns/{SLUG}").json()

    assert campaign["status"] == "draft"
    assert [stage["phase"] for stage in campaign["stages"]] == [
        "Research",
        "Strategy",
        "Strategy",
        "Plan",
        "Produce",
        "Produce",
    ]
    for stage in campaign["stages"]:
        assert set(stage) >= {
            "key",
            "phase",
            "state",
            "approval_policy",
            "latest_version",
            "stale",
        }
        assert stage["state"] == "pending"
        assert stage["latest_version"] is None


def test_workspace_shows_the_gate_the_run_halts_at(client: TestClient) -> None:
    """The whole point of the screen: a run stops and the person decides."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    campaign = client.get(f"/campaigns/{SLUG}").json()
    assert campaign["status"] == "awaiting_approval"

    states = {stage["key"]: stage["state"] for stage in campaign["stages"]}
    assert states["research"] == "completed"
    assert states["brand-strategy"] == "awaiting_approval"

    active = client.get("/runs").json()["runs"]
    assert [run["slug"] for run in active] == [SLUG]
    assert active[0]["run_id"] == run_id


def test_workspace_renders_full_deliverable_content_not_just_a_filename(
    client: TestClient,
) -> None:
    """The API exposed only names and sizes before this slice; now it serves content."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    body = client.get(f"/campaigns/{SLUG}/deliverables/brand-strategy.md").json()

    assert body["stage_key"] == "brand-strategy"
    assert body["stale"] is False
    assert body["content"].strip() != ""


def test_revising_produces_a_second_version_the_history_can_explain(
    client: TestClient,
) -> None:
    """Version history shows the feedback that produced each version (ADR-0015)."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    sent_back = client.post(
        f"/runs/{run_id}/revise",
        json={"stage_key": "brand-strategy", "feedback": "Too premium; we are mid-market."},
    )
    assert sent_back.status_code == 202
    _wait_for_status(client, run_id, "awaiting_approval")

    versions = client.get(f"/campaigns/{SLUG}/deliverables/brand-strategy.md/versions").json()[
        "versions"
    ]
    assert [version["version"] for version in versions] == [2, 1]
    newest = next(version for version in versions if version["version"] == 2)
    assert newest["feedback"] == "Too premium; we are mid-market."
    assert newest["feedback_source"] == "human"

    first = client.get(f"/campaigns/{SLUG}/deliverables/brand-strategy.md/versions/1").json()
    assert first["latest"] is False
    assert first["content"].strip() != ""


def test_approving_resumes_the_run_into_the_next_stage(client: TestClient) -> None:
    """Approving visibly continues the run, which is what the screen promises."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    approved = client.post(f"/runs/{run_id}/approve", json={"stage_key": "brand-strategy"})
    assert approved.status_code == 200
    _wait_for_status(client, run_id, "awaiting_approval")

    campaign = client.get(f"/campaigns/{SLUG}").json()
    states = {stage["key"]: stage["state"] for stage in campaign["stages"]}
    assert states["brand-strategy"] == "completed"
    assert states["campaign-strategy"] == "awaiting_approval"


def test_reopening_marks_downstream_stale_and_offers_a_rerun(client: TestClient) -> None:
    """Stale work is flagged, never silently regenerated (ADR-0015)."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "brand-strategy"})
    _wait_for_status(client, run_id, "awaiting_approval")

    reopened = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen",
        json={"feedback": "Reposition against the mid-market."},
    )
    assert reopened.status_code == 202
    _wait_for_status(client, reopened.json()["run_id"], "awaiting_approval")

    campaign = client.get(f"/campaigns/{SLUG}").json()
    stale = {stage["key"]: stage["stale"] for stage in campaign["stages"]}
    assert stale["campaign-strategy"] is True


def test_the_run_stream_replays_so_a_reopened_tab_reattaches(client: TestClient) -> None:
    """A closed and reopened tab must see the whole run, not only what came after."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")

    with client.stream("GET", f"/runs/{run_id}/stream") as stream:
        assert stream.status_code == 200
        frames = []
        for line in stream.iter_lines():
            if line.startswith("data: "):
                frames.append(line)
            if len(frames) >= 3:
                break

    assert len(frames) >= 3


def test_a_missing_deliverable_is_absent_rather_than_an_error(client: TestClient) -> None:
    """A stage that has not run yet is the ordinary state, and reads as empty."""
    response = client.get(f"/campaigns/{SLUG}/deliverables/asset-prompts.md")
    assert response.status_code == 404


def test_another_tenants_campaign_is_indistinguishable_from_a_missing_one(
    client: TestClient,
) -> None:
    """Cross-tenant access answers 404, so existence never leaks (ADR-0013)."""
    from marketing_os.entrypoints.api.app import app

    authenticate(app, tenant="org_rival")
    assert client.get(f"/campaigns/{SLUG}").status_code == 404


def test_a_failed_gate_names_the_fields_so_the_message_can_be_actionable(
    client: TestClient, repo: Path
) -> None:
    """The Workspace shows the refusal; a bare "gate failed" would not help anyone."""
    (repo / "tenants" / TENANT / "dna.md").write_text(PLACEHOLDER_DNA, encoding="utf-8")

    response = client.post(f"/campaigns/{SLUG}/run", json={})

    assert response.status_code == 409
    body = response.json()
    assert body["type"] == "gate_failed"
    assert body["missing_fields"], "the refusal must name what is missing"


def test_clearing_a_stale_stage_runs_that_stage_alone(client: TestClient) -> None:
    """The button says "Re-run this stage", so it must not redo the whole pipeline.

    Re-running everything would spend the tenant's allowance redoing work nobody
    asked to have redone, which is the thing ADR-0015 refuses to do on its own.
    What is pinned here is that a stage-scoped start is honoured: the run the
    interface asks for names one stage, and the engine runs that one.
    """
    started = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"})

    assert started.status_code == 202
    assert started.json()["stage"] == "research"
    _wait_for_status(client, started.json()["run_id"], "completed")

    campaign = client.get(f"/campaigns/{SLUG}").json()
    states = {stage["key"]: stage["state"] for stage in campaign["stages"]}
    assert states["research"] == "completed"
    assert states["brand-strategy"] == "pending", "only the named stage ran"
