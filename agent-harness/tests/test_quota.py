"""Enforced quota: work is refused before the model is called, not billed after.

The behaviour a business owner and the platform admin can observe through the
API (ADR-0020): spend accrues as the pipeline runs, `GET /usage` reports it
against the allowance, and once the allowance is gone every operation that would
trigger billable work answers 402 with a message that says why. The load-bearing
assertion is :func:`test_an_exhausted_tenant_makes_no_model_call_at_all` — a
ledger that merely *reported* an overspend would pass every other test here.

The caps sit alongside the allowance: a campaign cannot be re-run without limit,
and re-opening a stage is a run and is bounded too.

Everything is hermetic — a scripted chat model, a fake reviewer, an overridden
auth dependency — so nothing contacts a provider or an IdP. Every scripted reply
reports a round 1000 tokens at a round rate, so an assertion can say "two model
calls" and mean a cost of 2.0 rather than a float nobody can verify by eye.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from conftest import (
    OTHER_TENANT,
    SLUG,
    TENANT,
    authenticate,
    clear_prototype_adapters,
    deliverable_from,
    install_prototype_adapters,
    install_scripted_graph,
    prototype_adapters,
    write_all_agent_specs,
    write_call,
)
from marketing_os.config import Settings
from marketing_os.schemas import Usage

MODEL = "counted-model"
RATE = 0.001
REPORTED_TOKENS = {"input_tokens": 600, "output_tokens": 400, "total_tokens": 1000}


def _counting_handler(messages: list[BaseMessage], index: int) -> AIMessage:
    """Write the deliverable, reporting a known token cost on every reply.

    The usage metadata is what the ledger charges against, so it is scripted
    here rather than left to the fake model's default of reporting none.

    Args:
        messages: The conversation so far.
        index: The model-call index (unused).

    Returns:
        A ``write_file`` tool call, or a plain completion after the write.
    """
    if isinstance(messages[-1], ToolMessage):
        return AIMessage(
            content="Saved. Done.",
            usage_metadata=REPORTED_TOKENS,
            response_metadata={"model_name": MODEL},
        )
    path = deliverable_from(messages)
    message = write_call(path, f"# Deliverable\n\nContent for {path}.")
    message.usage_metadata = REPORTED_TOKENS
    message.response_metadata = {"model_name": MODEL}
    return message


def _make_client(repo: Path) -> TestClient:
    """Build a test client with fresh providers, acting as a verified owner.

    Args:
        repo: The hermetic repository root.

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


@pytest.fixture
def client(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a hermetic API client whose model calls each cost a known amount.

    The token rate and the allowance are set through the same environment
    variables an operator would use, so the test exercises the configured
    mechanism rather than a path only tests can reach.

    Args:
        repo: The hermetic repository root fixture.
        monkeypatch: The pytest monkeypatch fixture.

    Yields:
        An entered FastAPI test client.
    """
    monkeypatch.setenv("MARKETING_OS_ROOT", str(repo))
    monkeypatch.setenv("MARKETING_OS_TOKEN_RATES", f"{MODEL}=  {RATE}")
    monkeypatch.setenv("MARKETING_OS_ALLOWANCE", "1000")
    write_all_agent_specs(Settings(root=repo))
    install_scripted_graph(monkeypatch, handler=_counting_handler)
    from marketing_os.entrypoints.api.app import get_settings

    with _make_client(repo) as entered:
        yield entered
    get_settings.cache_clear()
    clear_prototype_adapters()


def _exhaust(client: TestClient, tenant: str = TENANT) -> None:
    """Spend a tenant's whole allowance, without running the pipeline to do it.

    Charging the ledger directly keeps each test about *what an exhausted tenant
    is refused* rather than about how many model calls it takes to get there,
    which would make every one of them fragile to the pipeline's shape.

    Args:
        client: The entered test client, whose providers hold the ledger.
        tenant: The tenant to exhaust.
    """
    from marketing_os.entrypoints.api.app import get_settings, get_usage_ledger

    ledger = get_usage_ledger()
    allowance = get_settings().usage_allowance
    ledger.record(tenant, slug=SLUG, model=MODEL, usage=_usage(round(allowance / RATE)))
    assert ledger.consumption(tenant).exhausted, "the fixture failed to spend the allowance"


def _scaffold_campaign(repo: Path, tenant: str, slug: str) -> None:
    """Give a tenant a second campaign with a complete goal, so its gate passes.

    Copies the fixture goal rather than writing a fresh one, so a change to what
    the gate requires does not need editing in two places.

    Args:
        repo: The hermetic repository root.
        tenant: The tenant the campaign belongs to.
        slug: The new campaign's slug.
    """
    source = repo / "tenants" / TENANT / "campaigns" / SLUG / "goal.md"
    goal = repo / "tenants" / tenant / "campaigns" / slug / "goal.md"
    goal.parent.mkdir(parents=True, exist_ok=True)
    goal.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    dna = repo / "tenants" / tenant / "dna.md"
    if not dna.is_file():
        dna.parent.mkdir(parents=True, exist_ok=True)
        dna.write_text(
            (repo / "tenants" / TENANT / "dna.md").read_text(encoding="utf-8"), encoding="utf-8"
        )


def _usage(tokens: int) -> Usage:
    """Build a usage record consuming a given number of input tokens.

    Args:
        tokens: How many input tokens the call consumed.

    Returns:
        The usage record.
    """
    return Usage(input_tokens=tokens)


def test_a_fresh_tenant_has_spent_nothing_of_their_allowance(client: TestClient) -> None:
    body = client.get("/usage").json()

    assert body["used"] == 0
    assert body["allowance"] == pytest.approx(1000.0)
    assert body["remaining"] == pytest.approx(1000.0)
    assert body["exhausted"] is False


def test_running_the_pipeline_records_spend_against_the_tenant(client: TestClient) -> None:
    """Every billable model call is recorded, so consumption is visible as work happens."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, run_id, "completed")

    body = client.get("/usage").json()

    assert body["used"] > 0
    assert body["remaining"] < body["allowance"]


def test_spend_is_attributed_to_the_campaign_it_was_spent_on(client: TestClient) -> None:
    """The ledger is the unit-economics dataset: what did this campaign cost?"""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, run_id, "completed")

    body = client.get("/usage").json()

    assert [campaign["slug"] for campaign in body["campaigns"]] == [SLUG]
    assert body["campaigns"][0]["used"] == pytest.approx(body["used"])


def test_usage_can_be_read_for_one_campaign(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, run_id, "completed")

    whole = client.get("/usage").json()["used"]
    scoped = client.get("/usage", params={"slug": SLUG}).json()["used"]

    assert scoped == pytest.approx(whole)
    assert client.get("/usage", params={"slug": "never-run"}).json()["used"] == 0


def test_recorded_units_and_cost_name_the_model_that_was_billed(client: TestClient) -> None:
    from marketing_os.entrypoints.api.app import get_usage_ledger

    run_id = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, run_id, "completed")

    entries = get_usage_ledger().entries(TENANT)

    assert entries, "the run recorded no ledger entries"
    charged = [entry for entry in entries if entry.units > 0]
    assert charged, "no entry recorded any billable units"
    assert all(entry.cost == pytest.approx(entry.units * RATE) for entry in charged)
    assert all(entry.stage_key == "research" for entry in entries)


def test_an_exhausted_tenant_is_refused_a_run_with_the_typed_402(client: TestClient) -> None:
    _exhaust(client)

    response = client.post(f"/campaigns/{SLUG}/run", json={})

    assert response.status_code == 402
    body = response.json()
    assert body["type"] == "quota_exhausted"
    assert body["allowance"] == pytest.approx(1000.0)
    assert "allowance" in body["message"]
    # The interface says how far past the line the business is, so both numbers
    # have to be on the refusal — not only the ceiling they hit.
    assert body["used"] >= body["allowance"]


def test_an_exhausted_tenant_makes_no_model_call_at_all(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The allowance is checked *before* the call, so a refusal costs nothing.

    A ledger that only recorded spend after the fact would satisfy every other
    assertion in this file and still let a runaway loop overspend, so this is the
    one that makes the check-before-call ordering real.
    """
    from marketing_os.entrypoints.api.app import get_usage_ledger

    _exhaust(client)
    spent_before = get_usage_ledger().consumption(TENANT).used
    calls: list[int] = []

    def recording_handler(messages: list[BaseMessage], index: int) -> AIMessage:
        """Record that the model was reached, which it must not be.

        Args:
            messages: The conversation so far (unused).
            index: The model-call index, recorded so the count is observable.

        Returns:
            A reply this test asserts is never produced.
        """
        calls.append(index)
        return AIMessage(content="never reached")

    install_scripted_graph(monkeypatch, handler=recording_handler)

    refused = client.post(f"/campaigns/{SLUG}/run", json={})

    assert refused.status_code == 402
    assert calls == [], "an exhausted tenant reached the model"
    assert get_usage_ledger().consumption(TENANT).used == pytest.approx(spent_before)


def test_an_exhausted_tenant_is_refused_a_revision_with_the_typed_402(
    client: TestClient,
) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    _exhaust(client)

    response = client.post(
        f"/runs/{run_id}/revise",
        json={"stage_key": "brand-strategy", "feedback": "anchor it to convenience"},
    )

    assert response.status_code == 402
    assert response.json()["type"] == "quota_exhausted"


def test_an_exhausted_tenant_is_refused_a_reopen(client: TestClient) -> None:
    run_id = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, run_id, "completed")
    _exhaust(client)

    response = client.post(
        f"/campaigns/{SLUG}/stages/research/reopen", json={"feedback": "go deeper"}
    )

    assert response.status_code == 402
    assert response.json()["type"] == "quota_exhausted"


def test_approving_is_not_refused_for_quota(client: TestClient) -> None:
    """Approving is a decision, and the owner must always be able to accept work."""
    run_id = client.post(f"/campaigns/{SLUG}/run", json={}).json()["run_id"]
    _wait_for_status(client, run_id, "awaiting_approval")
    _exhaust(client)

    response = client.post(f"/runs/{run_id}/approve", json={"stage_key": "brand-strategy"})

    assert response.status_code == 200


def test_an_exhausted_allowance_does_not_hide_a_failing_gate(client: TestClient) -> None:
    """The gate is about incomplete governance inputs, and is reported as such."""
    _exhaust(client)

    response = client.post("/campaigns/no-such-campaign/run", json={})

    assert response.status_code == 409
    assert response.json()["type"] == "gate_failed"


def test_one_tenants_exhausted_allowance_does_not_refuse_another(
    client: TestClient, repo: Path
) -> None:
    """An allowance is a fact about one business, so exhausting it isolates to it.

    The two tenants run *different* campaigns on purpose: sharing a slug would
    make the second request a ``run_conflict`` over a claimed campaign, and the
    409 would hide whether the allowance was consulted at all.
    """
    from marketing_os.entrypoints.api.app import app

    _exhaust(client, OTHER_TENANT)
    _scaffold_campaign(repo, OTHER_TENANT, "rival-spring")

    first = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"})
    assert first.status_code == 202
    _wait_for_status(client, first.json()["run_id"], "completed")

    authenticate(app, OTHER_TENANT)
    assert client.post("/campaigns/rival-spring/run", json={}).status_code == 402


def test_a_tenant_cannot_read_another_tenants_spend(client: TestClient) -> None:
    from marketing_os.entrypoints.api.app import app

    _exhaust(client, OTHER_TENANT)

    assert client.get("/usage").json()["used"] == 0
    authenticate(app, OTHER_TENANT)
    assert client.get("/usage").json()["used"] > 0


def test_reading_usage_requires_an_identity(client: TestClient, repo: Path) -> None:
    from marketing_os.entrypoints.api.app import app, get_identity

    app.dependency_overrides.pop(get_identity, None)

    assert client.get("/usage").status_code == 401


def test_a_campaign_cannot_be_run_past_its_run_cap(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The companion cap to the revision limit: a whole campaign is bounded too."""
    from marketing_os.entrypoints.api.app import get_settings

    monkeypatch.setattr(get_settings(), "max_runs_per_campaign", 1)
    first = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, first, "completed")

    response = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"})

    assert response.status_code == 409
    assert response.json()["type"] == "run_limit_reached"
    assert "run limit" in response.json()["message"]


def test_reopening_a_stage_is_bounded_by_the_run_cap(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-opening starts a run, so a change of mind is not an unbounded way to spend."""
    from marketing_os.entrypoints.api.app import get_settings

    run_id = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, run_id, "completed")
    monkeypatch.setattr(get_settings(), "max_runs_per_campaign", 1)

    response = client.post(
        f"/campaigns/{SLUG}/stages/research/reopen", json={"feedback": "go deeper"}
    )

    assert response.status_code == 409
    assert response.json()["type"] == "run_limit_reached"


def test_the_run_cap_is_per_campaign_not_per_tenant(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    from marketing_os.entrypoints.api.app import get_settings

    monkeypatch.setattr(get_settings(), "max_runs_per_campaign", 1)
    first = client.post(f"/campaigns/{SLUG}/run", json={"stage": "research"}).json()["run_id"]
    _wait_for_status(client, first, "completed")
    _scaffold_campaign(repo, TENANT, "second")

    assert client.post("/campaigns/second/run", json={"stage": "research"}).status_code == 202


async def test_a_run_in_flight_halts_when_the_allowance_runs_out(
    settings: Settings, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cap binds the graph, not only the HTTP edge (ADR-0020).

    An endpoint check alone would let a run that was within its allowance when
    it started spend arbitrarily far past it, because nothing re-asks once the
    pipeline is moving. Driven through the runner rather than over HTTP so the
    halt is observable without a round trip per stage.
    """
    from marketing_os.adapters.usage import InMemoryUsageLedger
    from marketing_os.errors import QuotaExhaustedError
    from marketing_os.graph.runner import arun_campaign

    settings.token_rates = {MODEL: RATE}
    settings.usage_allowance = 1.0
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=_counting_handler)
    ledger = InMemoryUsageLedger(settings)

    with pytest.raises(QuotaExhaustedError) as raised:
        await arun_campaign(
            settings,
            TENANT,
            SLUG,
            **{**prototype_adapters(settings.root), "usage_ledger": ledger},
        )

    assert raised.value.http_status == 402
    assert ledger.consumption(TENANT).exhausted
    produced = settings.tenant_dir(TENANT) / "campaigns" / SLUG
    assert not (produced / "asset-prompts.md").is_file(), "the run spent past its allowance"


async def test_work_already_done_is_still_charged_when_a_run_halts(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recording happens after each call, so a halted run is billed for what it used."""
    from marketing_os.adapters.usage import InMemoryUsageLedger
    from marketing_os.errors import QuotaExhaustedError
    from marketing_os.graph.runner import arun_campaign

    settings.token_rates = {MODEL: RATE}
    settings.usage_allowance = 1.0
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=_counting_handler)
    ledger = InMemoryUsageLedger(settings)

    with pytest.raises(QuotaExhaustedError):
        await arun_campaign(
            settings,
            TENANT,
            SLUG,
            **{**prototype_adapters(settings.root), "usage_ledger": ledger},
        )

    charged = [entry for entry in ledger.entries(TENANT) if entry.units > 0]
    assert charged, "the halted run recorded nothing for the work it did"
    assert all(entry.slug == SLUG for entry in charged)


async def test_a_run_within_its_allowance_completes_uninterrupted(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check must not refuse work a tenant can afford."""
    from marketing_os.adapters.usage import InMemoryUsageLedger
    from marketing_os.graph.runner import arun_campaign

    settings.token_rates = {MODEL: RATE}
    settings.usage_allowance = 1000.0
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=_counting_handler)
    ledger = InMemoryUsageLedger(settings)

    result = await arun_campaign(
        settings,
        TENANT,
        SLUG,
        stage="research",
        **{**prototype_adapters(settings.root), "usage_ledger": ledger},
    )

    assert [stage.stage for stage in result.stages] == ["research"]
    assert ledger.consumption(TENANT).used > 0


async def test_a_run_without_a_ledger_is_not_refused(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An uncharged run is legal (ADR-0020) and must work rather than fail closed."""
    from marketing_os.graph.runner import arun_campaign

    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=_counting_handler)

    result = await arun_campaign(
        settings, TENANT, SLUG, stage="research", **prototype_adapters(settings.root)
    )

    assert [stage.stage for stage in result.stages] == ["research"]


async def test_a_run_cancelled_mid_call_is_still_charged_for_it(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancelling must not be a way to consume tokens for free.

    The charge is recorded in a ``finally``, so it happens on the way out of an
    aborted call as well as a completed one. The model is held open inside the
    call and the run cancelled there, which is the only point at which tokens
    could have been consumed with no entry written.
    """
    import asyncio

    from conftest import BlockingChatModel
    from marketing_os.adapters.usage import InMemoryUsageLedger
    from marketing_os.graph.runner import arun_campaign

    settings.token_rates = {MODEL: RATE}
    write_all_agent_specs(settings)
    model = BlockingChatModel()
    install_scripted_graph(monkeypatch, model_factory=lambda: model)
    ledger = InMemoryUsageLedger(settings)

    task = asyncio.create_task(
        arun_campaign(
            settings,
            TENANT,
            SLUG,
            stage="research",
            **{**prototype_adapters(settings.root), "usage_ledger": ledger},
        )
    )
    await asyncio.wait_for(model.entered.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert model.was_cancelled, "the model call was not the thing cancelled"
    charged = ledger.entries(TENANT)
    assert len(charged) == 1, "the aborted call wrote no ledger entry"
    assert charged[0].stage_key == "research"


async def test_a_deliverable_written_before_the_halt_is_not_lost(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running out mid-pipeline must not discard work the tenant already paid for."""
    from marketing_os.adapters.usage import InMemoryUsageLedger
    from marketing_os.errors import QuotaExhaustedError
    from marketing_os.graph.runner import arun_campaign

    settings.token_rates = {MODEL: RATE}
    settings.usage_allowance = 1.0
    write_all_agent_specs(settings)
    install_scripted_graph(monkeypatch, handler=_counting_handler)
    ledger = InMemoryUsageLedger(settings)

    with pytest.raises(QuotaExhaustedError):
        await arun_campaign(
            settings,
            TENANT,
            SLUG,
            **{**prototype_adapters(settings.root), "usage_ledger": ledger},
        )

    research = settings.tenant_dir(TENANT) / "campaigns" / SLUG / "research.md"
    assert research.is_file(), "the stage that completed before the halt lost its deliverable"
