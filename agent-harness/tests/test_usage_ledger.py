"""The Usage Ledger: what a call cost, charged to its tenant, checked before the next.

One conformance suite over the :class:`~marketing_os.ports.UsageLedger` port,
parametrised so the same assertions run against the in-memory ledger and, when
Docker is available, the real Postgres one. That is deliberate: the ledger is the
thing standing between a runaway loop and a real bill, so "both stores refuse at
the same point" is a property worth pinning rather than assuming.

The behaviour pinned here is what an owner and the platform admin can observe:
spend accumulates, an exhausted allowance refuses the next call, one tenant's
spend is invisible to another, and the same rows total per campaign as well as
per tenant.

The rate and the token counts are deliberately round, so an assertion reads as
the arithmetic it is checking: 1000 tokens at 0.001 each is a cost of 1.0.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from conftest import OTHER_TENANT, SLUG, TENANT
from marketing_os.adapters.usage import InMemoryUsageLedger
from marketing_os.config import Settings
from marketing_os.errors import QuotaExhaustedError
from marketing_os.schemas import Usage

MODEL = "deepseek-v4-pro"
RATE = 0.001
THOUSAND = Usage(input_tokens=600, output_tokens=400)


def _settings(allowance: float = 10.0) -> Settings:
    """Build settings with a round token rate and a known allowance.

    Args:
        allowance: The platform-wide allowance every tenant gets.

    Returns:
        Settings the ledger prices calls and refuses them against.
    """
    return Settings(usage_allowance=allowance, token_rates={MODEL: RATE})


LedgerFactory = Callable[[Settings], Any]


@pytest.fixture
def in_memory_ledger() -> LedgerFactory:
    """Return a factory building the in-memory ledger.

    Returns:
        A callable taking settings and returning a ledger.
    """
    return InMemoryUsageLedger


@pytest.fixture
def postgres_ledger(postgres_pool: Any) -> Iterator[LedgerFactory]:
    """Return a factory building the Postgres ledger over a truncated database.

    Both tenants are registered first, because a business exists in the
    directory before it can spend anything — and a per-tenant allowance is
    recorded *on* that row, so a ledger over an unregistered tenant would have
    nowhere to write one.

    Args:
        postgres_pool: The containerised pool fixture, which skips without Docker.

    Yields:
        A callable taking settings and returning a ledger.
    """
    from marketing_os.adapters.postgres.tenants import PostgresTenantDirectory
    from marketing_os.adapters.postgres.usage import PostgresUsageLedger

    directory = PostgresTenantDirectory(postgres_pool)
    for tenant in (TENANT, OTHER_TENANT):
        with postgres_pool.connection() as connection:
            connection.execute(
                "INSERT INTO tenants (tenant_id, name, external_auth_id) VALUES (%s, %s, %s) "
                "ON CONFLICT (external_auth_id) DO NOTHING",
                (tenant, tenant, tenant),
            )
    assert directory.get(TENANT) is not None

    yield lambda settings: PostgresUsageLedger(postgres_pool, settings)


@pytest.fixture(
    params=[
        pytest.param("in_memory_ledger", id="in-memory"),
        pytest.param("postgres_ledger", id="postgres", marks=pytest.mark.slow),
    ]
)
def ledger_factory(request: pytest.FixtureRequest) -> LedgerFactory:
    """Yield each ledger adapter in turn, so one suite covers both.

    Args:
        request: The pytest request, naming the fixture to resolve.

    Returns:
        The adapter factory under test.
    """
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


@pytest.fixture
def ledger(ledger_factory: LedgerFactory) -> Any:
    """Build the adapter under test with the suite's standard settings.

    Args:
        ledger_factory: The parametrised adapter factory.

    Returns:
        A ledger with a 10.0 allowance and a 0.001 token rate.
    """
    return ledger_factory(_settings())


def test_a_recorded_call_costs_tokens_times_the_configured_rate(ledger: Any) -> None:
    entry = ledger.record(TENANT, slug=SLUG, stage_key="research", model=MODEL, usage=THOUSAND)

    assert entry.units == 1000
    assert entry.cost == pytest.approx(1.0)
    assert entry.model == MODEL


def test_an_unpriced_model_is_costed_rather_than_treated_as_free(ledger: Any) -> None:
    """A forgotten rate should under-report spend, never hide the call entirely."""
    entry = ledger.record(TENANT, slug=SLUG, model="some-new-model", usage=THOUSAND)

    assert entry.units == 1000
    assert entry.cost > 0


def test_a_call_reporting_no_tokens_is_still_recorded(ledger: Any) -> None:
    """The ledger should show that a call happened even when it cost nothing."""
    entry = ledger.record(TENANT, slug=SLUG, model=MODEL, usage=None)

    assert entry.cost == 0.0
    assert len(ledger.entries(TENANT)) == 1


def test_cached_prompt_tokens_are_not_charged_at_the_prompt_rate(ledger: Any) -> None:
    cached = Usage(input_tokens=100, output_tokens=0, cache_read_input_tokens=900)

    entry = ledger.record(TENANT, slug=SLUG, model=MODEL, usage=cached)

    assert entry.units == 100


def test_spend_accumulates_across_calls(ledger: Any) -> None:
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    assert ledger.consumption(TENANT).used == pytest.approx(2.0)


def test_consumption_reports_what_is_left_of_the_allowance(ledger: Any) -> None:
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    report = ledger.consumption(TENANT)

    assert report.allowance == pytest.approx(10.0)
    assert report.remaining == pytest.approx(9.0)
    assert not report.exhausted


def test_a_tenant_within_their_allowance_may_make_another_call(ledger: Any) -> None:
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    ledger.check(TENANT)


def test_an_exhausted_allowance_refuses_the_next_call(ledger_factory: LedgerFactory) -> None:
    spent = ledger_factory(_settings(allowance=1.0))
    spent.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    with pytest.raises(QuotaExhaustedError) as raised:
        spent.check(TENANT)

    assert raised.value.used == pytest.approx(1.0)
    assert raised.value.allowance == pytest.approx(1.0)
    assert raised.value.http_status == 402


def test_an_overspent_tenant_has_no_negative_balance_to_explain(
    ledger_factory: LedgerFactory,
) -> None:
    spent = ledger_factory(_settings(allowance=0.5))
    spent.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    assert spent.consumption(TENANT).remaining == 0.0


def test_a_fresh_tenant_has_spent_nothing_and_may_work(ledger: Any) -> None:
    report = ledger.consumption(TENANT)

    assert report.used == 0.0
    assert report.campaigns == []
    ledger.check(TENANT)


def test_one_tenants_spend_is_invisible_to_another(ledger: Any) -> None:
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    assert ledger.consumption(OTHER_TENANT).used == 0.0
    assert ledger.entries(OTHER_TENANT) == []


def test_one_tenant_exhausting_their_allowance_does_not_block_another(
    ledger_factory: LedgerFactory,
) -> None:
    shared = ledger_factory(_settings(allowance=1.0))
    shared.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    shared.check(OTHER_TENANT)


def test_the_same_rows_total_per_campaign(ledger: Any) -> None:
    """The ledger is the unit-economics dataset: what did each campaign cost?"""
    ledger.record(TENANT, slug="spring", model=MODEL, usage=THOUSAND)
    ledger.record(TENANT, slug="spring", model=MODEL, usage=THOUSAND)
    ledger.record(TENANT, slug="autumn", model=MODEL, usage=THOUSAND)

    report = ledger.consumption(TENANT)

    assert report.used == pytest.approx(3.0)
    assert [(item.slug, item.used) for item in report.campaigns] == [
        ("spring", pytest.approx(2.0)),
        ("autumn", pytest.approx(1.0)),
    ]


def test_consumption_can_be_scoped_to_one_campaign(ledger: Any) -> None:
    ledger.record(TENANT, slug="spring", model=MODEL, usage=THOUSAND)
    ledger.record(TENANT, slug="autumn", model=MODEL, usage=THOUSAND)

    assert ledger.consumption(TENANT, "spring").used == pytest.approx(1.0)


def test_entries_are_queryable_per_tenant_and_per_campaign(ledger: Any) -> None:
    ledger.record(TENANT, slug="spring", stage_key="research", model=MODEL, usage=THOUSAND)
    ledger.record(TENANT, slug="autumn", stage_key="research", model=MODEL, usage=THOUSAND)

    assert len(ledger.entries(TENANT)) == 2
    scoped = ledger.entries(TENANT, "spring")
    assert [entry.slug for entry in scoped] == ["spring"]
    assert scoped[0].stage_key == "research"


def test_entries_come_back_newest_first(ledger: Any) -> None:
    ledger.record(TENANT, slug="first", model=MODEL, usage=THOUSAND)
    ledger.record(TENANT, slug="second", model=MODEL, usage=THOUSAND)

    assert [entry.slug for entry in ledger.entries(TENANT)] == ["second", "first"]


def test_a_call_not_tied_to_a_campaign_still_counts_against_the_allowance(ledger: Any) -> None:
    """It is omitted from the per-campaign breakdown, not from the tenant total."""
    ledger.record(TENANT, model=MODEL, usage=THOUSAND)

    report = ledger.consumption(TENANT)

    assert report.used == pytest.approx(1.0)
    assert report.campaigns == []


def test_a_tenants_own_allowance_overrides_the_platform_default(ledger: Any) -> None:
    """Raising one design partner's cap is a row, not a deploy (ADR-0020)."""
    ledger.set_allowance(TENANT, 1.0)
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    with pytest.raises(QuotaExhaustedError):
        ledger.check(TENANT)
    ledger.check(OTHER_TENANT)


def test_clearing_an_override_falls_back_to_the_platform_default(ledger: Any) -> None:
    ledger.set_allowance(TENANT, 1.0)
    ledger.record(TENANT, slug=SLUG, model=MODEL, usage=THOUSAND)

    ledger.set_allowance(TENANT, None)

    ledger.check(TENANT)
    assert ledger.consumption(TENANT).allowance == pytest.approx(10.0)
