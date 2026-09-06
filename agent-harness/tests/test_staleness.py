"""Downstream staleness: re-opening an approved decision flags what rests on it.

Campaigns get edited weeks later, after work has been built on top of them. The
failure this prevents is quiet and expensive — creative resting on a strategy
that was superseded, with nothing in the interface saying so (ADR-0015).

What is pinned here is that re-opening a stage marks everything downstream
**stale rather than regenerating it**: no model is called on a stale
deliverable's behalf, the owner re-runs the stale stages when they are ready, and
re-running appends a version rather than overwriting one.

The pure-function tests fix the derivation; the API tests prove the same
behaviour through the endpoints a frontend calls, with a scripted model and a
fake reviewer so nothing here touches a network.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from conftest import (
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
from marketing_os.adapters.deliverables import InMemoryDeliverableStore
from marketing_os.campaign.progress import campaign_progress
from marketing_os.config import Settings
from marketing_os.governance.staleness import stale_stages


def _numbered_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write a deliverable whose body records which model call produced it.

    Args:
        messages: The conversation so far.
        index: The model-call index.

    Returns:
        A ``write_file`` tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(content="Saved. Done.")
    path = deliverable_from(messages)
    return write_call(path, f"# Deliverable\n\nDraft {index} for {path}.")


def _produce(store: InMemoryDeliverableStore, *stage_keys: str) -> None:
    """Append one version of each named stage's deliverable, in the order given.

    Args:
        store: The deliverable store to append into.
        *stage_keys: The stages to produce a deliverable for, oldest first.
    """
    for stage_key in stage_keys:
        store.append(TENANT, SLUG, stage_key, f"# {stage_key}")


def test_nothing_is_stale_when_every_stage_was_produced_in_pipeline_order() -> None:
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy", "campaign-strategy")

    assert stale_stages(store, TENANT, SLUG) == []


def test_reproducing_an_upstream_stage_makes_everything_downstream_stale() -> None:
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy", "campaign-strategy", "performance-plan")

    store.append(TENANT, SLUG, "brand-strategy", "# revised")

    assert stale_stages(store, TENANT, SLUG) == ["campaign-strategy", "performance-plan"]


def test_a_reopened_stage_is_not_itself_stale() -> None:
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy", "campaign-strategy")

    store.append(TENANT, SLUG, "brand-strategy", "# revised")

    assert "brand-strategy" not in stale_stages(store, TENANT, SLUG)


def test_upstream_of_the_reopened_stage_stays_fresh() -> None:
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy", "campaign-strategy")

    store.append(TENANT, SLUG, "campaign-strategy", "# revised")

    assert stale_stages(store, TENANT, SLUG) == []


def test_re_running_a_stale_stage_clears_its_flag() -> None:
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy", "campaign-strategy", "performance-plan")
    store.append(TENANT, SLUG, "brand-strategy", "# revised")

    store.append(TENANT, SLUG, "campaign-strategy", "# re-run")

    assert stale_stages(store, TENANT, SLUG) == ["performance-plan"]


def test_a_stage_that_never_produced_a_deliverable_is_not_stale() -> None:
    """Staleness describes work that exists and is now superseded, not absent work."""
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy")

    store.append(TENANT, SLUG, "research", "# revised")

    assert stale_stages(store, TENANT, SLUG) == ["brand-strategy"]


def _make_client(repo: Path) -> TestClient:
    """Build a TestClient bound to the hermetic repo with caches cleared.

    Args:
        repo: The hermetic repository root fixture.

    Returns:
        A configured (not yet entered) FastAPI test client.
    """
    from marketing_os.entrypoints.api.app import app, get_settings

    get_settings.cache_clear()
    install_prototype_adapters(repo)
    authenticate(app)
    return TestClient(app)


def _wait_for_status(client: TestClient, run_id: str, target: str) -> dict:
    """Poll a run's status until it reaches ``target`` or time out.

    Args:
        client: The entered test client.
        run_id: The run id to poll.
        target: The status to wait for.

    Returns:
        The status payload once it matches ``target``.
    """
    for _ in range(300):
        response = client.get(f"/runs/{run_id}")
        if response.status_code == 200 and response.json()["status"] == target:
            return response.json()
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached status {target!r}")


def _advance_to(client: TestClient, run_id: str, stage_key: str) -> None:
    """Approve each Approval Gate until the run halts at ``stage_key``.

    Args:
        client: The entered test client.
        run_id: The run to drive.
        stage_key: The stage to stop approving at.
    """
    for _ in range(len(("research", "brand-strategy", "campaign-strategy", "performance-plan"))):
        status = _wait_for_status(client, run_id, "awaiting_approval")
        waiting = status["stage"] if status.get("stage") else _waiting_stage(client)
        if waiting == stage_key:
            return
        client.post(f"/runs/{run_id}/approve", json={"stage_key": waiting})
    raise AssertionError(f"run {run_id} never reached stage {stage_key!r}")


def _waiting_stage(client: TestClient) -> str:
    """Return the stage a campaign is currently halted at.

    Args:
        client: The entered test client.

    Returns:
        The waiting stage key.
    """
    body = client.get(f"/campaigns/{SLUG}/stages").json()
    waiting = [s["key"] for s in body["stages"] if s["state"] == "awaiting_approval"]
    assert waiting, "no stage is awaiting approval"
    return waiting[0]


def _stage_states(client: TestClient) -> dict[str, str]:
    """Return each stage's reported state.

    Args:
        client: The entered test client.

    Returns:
        A map of stage key to state.
    """
    body = client.get(f"/campaigns/{SLUG}/stages").json()
    return {stage["key"]: stage["state"] for stage in body["stages"]}


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
    from marketing_os.entrypoints.api.app import get_settings

    with _make_client(repo) as entered:
        yield entered
    get_settings.cache_clear()
    clear_prototype_adapters()


def _run_to_creative_brief(client: TestClient) -> str:
    """Run a campaign through to the creative brief, approving every gate.

    Args:
        client: The entered test client.

    Returns:
        The run id, halted at the creative-brief gate.
    """
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _advance_to(client, run_id, "creative-brief")
    return run_id


def test_reopening_an_approved_stage_marks_everything_downstream_stale(
    client: TestClient,
) -> None:
    run_id = _run_to_creative_brief(client)
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "creative-brief"})
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "asset-prompts"})
    _wait_for_status(client, run_id, "completed")

    response = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen",
        json={"feedback": "Anchor it to convenience, not premium."},
    )

    assert response.status_code == 202
    reopened_run = response.json()["run_id"]
    _wait_for_status(client, reopened_run, "awaiting_approval")
    states = _stage_states(client)
    assert states["campaign-strategy"] == "stale"
    assert states["performance-plan"] == "stale"
    assert states["creative-brief"] == "stale"
    assert states["asset-prompts"] == "stale"


def test_a_stale_deliverable_is_not_regenerated(client: TestClient) -> None:
    """No model is called on a stale deliverable's behalf — that is the whole point."""
    _run_to_creative_brief(client)
    before = client.get(f"/campaigns/{SLUG}/deliverables/campaign-strategy.md/versions").json()

    response = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen", json={"feedback": "Mid-market."}
    )
    _wait_for_status(client, response.json()["run_id"], "awaiting_approval")

    after = client.get(f"/campaigns/{SLUG}/deliverables/campaign-strategy.md/versions").json()
    assert after["versions"] == before["versions"]


def test_staleness_is_reported_on_the_deliverable_listing(client: TestClient) -> None:
    _run_to_creative_brief(client)
    response = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen", json={"feedback": "Mid-market."}
    )
    _wait_for_status(client, response.json()["run_id"], "awaiting_approval")

    body = client.get(f"/campaigns/{SLUG}/deliverables").json()

    stale = {entry["stage_key"]: entry["stale"] for entry in body["deliverables"]}
    assert stale["brand-strategy"] is False
    assert stale["campaign-strategy"] is True
    assert stale["performance-plan"] is True


def test_reading_a_stale_deliverable_says_so(client: TestClient) -> None:
    _run_to_creative_brief(client)
    response = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen", json={"feedback": "Mid-market."}
    )
    _wait_for_status(client, response.json()["run_id"], "awaiting_approval")

    body = client.get(f"/campaigns/{SLUG}/deliverables/campaign-strategy.md").json()

    assert body["stale"] is True


def _reopen_and_approve(client: TestClient, stage_key: str, feedback: str) -> None:
    """Re-open a stage, wait for its gate, and approve the revision.

    Args:
        client: The entered test client.
        stage_key: The stage to re-open.
        feedback: What the owner wants changed.
    """
    run_id = client.post(
        f"/campaigns/{SLUG}/stages/{stage_key}/reopen", json={"feedback": feedback}
    ).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/approve", json={"stage_key": stage_key})
    _wait_for_status(client, run_id, "completed")


def test_re_running_a_stale_stage_clears_its_flag_and_appends_a_version(
    client: TestClient,
) -> None:
    """The owner re-runs the stale work when they are ready, one stage at a time."""
    _run_to_creative_brief(client)
    _reopen_and_approve(client, "brand-strategy", "Mid-market, not premium.")
    assert _stage_states(client)["campaign-strategy"] == "stale"

    rerun = client.post(f"/campaigns/{SLUG}/run", json={"stage": "campaign-strategy"}).json()
    _wait_for_status(client, rerun["run_id"], "awaiting_approval")
    client.post(f"/runs/{rerun['run_id']}/approve", json={"stage_key": "campaign-strategy"})
    _wait_for_status(client, rerun["run_id"], "completed")

    assert _stage_states(client)["campaign-strategy"] == "completed"
    versions = client.get(f"/campaigns/{SLUG}/deliverables/campaign-strategy.md/versions").json()
    assert [version["version"] for version in versions["versions"]] == [2, 1]


async def _campaign_status(repo: Path, *, waiting: str | None) -> str:
    """Return the campaign's lifecycle status, asked of the domain directly.

    Lifecycle derivation lives in :mod:`marketing_os.campaign.progress`, so this
    calls it rather than driving a ``TestClient`` — the status is a fact about
    the business's work, and asserting it should not need an HTTP round trip.

    ``waiting`` is named by each caller rather than defaulted, because a
    campaign holding at a gate is ``awaiting_approval`` before staleness is ever
    consulted. A test about staleness that quietly stubbed a waiting stage would
    pass whether or not staleness blocked anything.

    Args:
        repo: The hermetic repository root the deliverables were written under.
        waiting: The stage a live run is holding at, or ``None`` when the run
            has finished and nothing is waiting on a person.

    Returns:
        The campaign's lifecycle status.
    """
    from marketing_os.adapters.deliverables import FilesystemDeliverableStore

    async def waiting_stage() -> str | None:
        return waiting

    progress = await campaign_progress(
        FilesystemDeliverableStore(repo),
        TENANT,
        SLUG,
        human_gate_stages=None,
        awaiting_stage=waiting_stage,
    )
    return progress.status


async def test_a_campaign_reads_approved_once_every_stage_is_approved(
    client: TestClient, repo: Path
) -> None:
    run_id = _run_to_creative_brief(client)
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "creative-brief"})
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "asset-prompts"})
    _wait_for_status(client, run_id, "completed")

    assert await _campaign_status(repo, waiting=None) == "approved"


async def test_a_campaign_with_stale_work_is_not_approved(client: TestClient, repo: Path) -> None:
    run_id = _run_to_creative_brief(client)
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "creative-brief"})
    _wait_for_status(client, run_id, "awaiting_approval")
    client.post(f"/runs/{run_id}/approve", json={"stage_key": "asset-prompts"})
    _wait_for_status(client, run_id, "completed")

    reopened = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen", json={"feedback": "Mid-market."}
    ).json()["run_id"]
    _wait_for_status(client, reopened, "awaiting_approval")

    assert await _campaign_status(repo, waiting=None) == "running", (
        "stale work must un-approve the campaign on its own, with nothing waiting on a person"
    )


def test_reopening_a_stage_that_produced_nothing_is_refused(client: TestClient) -> None:
    response = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen", json={"feedback": "Mid-market."}
    )

    assert response.status_code == 404


def test_another_tenants_campaign_cannot_be_reopened(client: TestClient, repo: Path) -> None:
    _run_to_creative_brief(client)
    from marketing_os.entrypoints.api.app import app

    authenticate(app, tenant="org_rival")

    response = client.post(
        f"/campaigns/{SLUG}/stages/brand-strategy/reopen", json={"feedback": "Mid-market."}
    )

    assert response.status_code == 404


def test_staleness_holds_when_every_version_shares_one_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wall-clock ties must not silently un-stale downstream work.

    Timestamps collide in practice — microsecond resolution ties under rapid
    writes, and Postgres ``now()`` is fixed for a whole transaction. Freezing the
    clock is the honest way to state that: if staleness rested on ``created_at``,
    a re-opened decision would leave the work beneath it looking fresh, which is
    exactly the silent inconsistency the flag exists to prevent.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
    """
    monkeypatch.setattr(
        "marketing_os.adapters.deliverables.now_timestamp",
        lambda: "2026-09-03T00:00:00+00:00",
    )
    store = InMemoryDeliverableStore()
    _produce(store, "research", "brand-strategy", "campaign-strategy")

    store.append(TENANT, SLUG, "research", "# revised")

    assert stale_stages(store, TENANT, SLUG) == ["brand-strategy", "campaign-strategy"]
