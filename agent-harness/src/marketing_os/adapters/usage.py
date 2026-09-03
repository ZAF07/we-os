"""Usage ledger adapters — where what a tenant spent is recorded and enforced.

Implements the :class:`~marketing_os.ports.UsageLedger` port (ADR-0020). The
ledger is **append-only**: an entry records what one billable call cost, and
nothing in this module edits or deletes one. That is what makes it usable as the
unit-economics dataset — "what did this campaign cost?" is a sum over rows that
were never rewritten.

Costing lives here rather than in each adapter, so a call is priced identically
whichever store is behind the port, and no caller can record a call at a price of
its own choosing.

The allowance resolves in two steps: the platform-wide default from settings,
overridden by a per-tenant allowance when the directory holds one. Raising one
design partner's cap is therefore a row rather than a deploy, while the decision
about how an allowance is *presented* — credits, fair use, metered billing —
stays deferred.
"""

from __future__ import annotations

from datetime import UTC, datetime

from marketing_os.adapters.documents import validate_tenant_id
from marketing_os.config import Settings
from marketing_os.errors import QuotaExhaustedError
from marketing_os.schemas import CampaignConsumption, Consumption, LedgerEntry, Usage

TOKENS = "tokens"


def now_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 timestamp.

    Returns:
        The timestamp every adapter stamps a new entry with, so the format is
        identical whichever store is behind the port.
    """
    return datetime.now(UTC).isoformat()


def billable_tokens(usage: Usage | None) -> int:
    """Return how many tokens a call is charged for.

    Cache reads are excluded because the provider does not bill them at the
    prompt rate, and counting them would overstate what the platform actually
    spent. Cache *creation* is charged, because it is billed.

    Args:
        usage: The token counts the call reported, or ``None`` when it reported
            none.

    Returns:
        The chargeable token count, zero when there is nothing to charge.
    """
    if usage is None:
        return 0
    return usage.input_tokens + usage.output_tokens + usage.cache_creation_input_tokens


def cost_of(settings: Settings, model: str, usage: Usage | None) -> float:
    """Return what one model call cost, at the configured rate for its model.

    Args:
        settings: The harness settings holding the per-model token rates.
        model: The model identifier the provider billed for.
        usage: The token counts the call consumed.

    Returns:
        The call's cost in the platform's accounting currency.
    """
    return billable_tokens(usage) * settings.token_rate(model)


def total_of(entries: list[LedgerEntry]) -> float:
    """Return the total cost of a set of ledger entries.

    Args:
        entries: The entries to total.

    Returns:
        Their summed cost.
    """
    return sum(entry.cost for entry in entries)


def rank_campaigns(totals: dict[str, float]) -> list[CampaignConsumption]:
    """Order per-campaign totals dearest first, ties broken by slug.

    Both adapters end up with the same ``{slug: total}`` mapping — one by
    summing entries in the process, the other from a ``GROUP BY`` — so the order
    the breakdown comes back in is decided here once. Sorting in Python rather
    than in SQL is what keeps the two from disagreeing about it.

    Args:
        totals: The cost per campaign slug.

    Returns:
        One total per campaign, highest spend first.
    """
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return [CampaignConsumption(slug=slug, used=used) for slug, used in ranked]


def per_campaign(entries: list[LedgerEntry]) -> list[CampaignConsumption]:
    """Total a set of entries by the campaign they were spent on, dearest first.

    Entries not tied to a campaign are omitted rather than grouped under a
    placeholder slug: the breakdown answers "what did each campaign cost?", and
    inventing a campaign that does not exist to hold the remainder would make
    the per-campaign totals stop summing to anything meaningful. The tenant
    total still includes them.

    Args:
        entries: The entries to group.

    Returns:
        One total per campaign, highest spend first.
    """
    totals: dict[str, float] = {}
    for entry in entries:
        if entry.slug is None:
            continue
        totals[entry.slug] = totals.get(entry.slug, 0.0) + entry.cost
    return rank_campaigns(totals)


def build_entry(
    settings: Settings,
    tenant: str,
    slug: str | None,
    stage_key: str | None,
    model: str,
    usage: Usage | None,
) -> LedgerEntry:
    """Build the entry recording one billable model call.

    Shared by every adapter so a call is priced and shaped in one place rather
    than re-derived per backend.

    Args:
        settings: The harness settings holding the per-model token rates.
        tenant: The tenant to charge.
        slug: The campaign the call was made for, if any.
        stage_key: The pipeline stage the call belongs to, if any.
        model: The model identifier the provider billed for.
        usage: The token counts the call consumed.

    Returns:
        The entry to append, carrying its assigned cost.
    """
    return LedgerEntry(
        tenant_id=tenant,
        slug=slug,
        stage_key=stage_key,
        kind=TOKENS,
        model=model,
        units=billable_tokens(usage),
        cost=cost_of(settings, model, usage),
        recorded_at=now_timestamp(),
    )


def refuse_when_exhausted(consumption: Consumption) -> None:
    """Raise the typed quota failure when a tenant's allowance is spent.

    Shared by every adapter so both stores refuse at exactly the same point,
    rather than one of them being a rounding error more generous.

    Args:
        consumption: The tenant's spend against their allowance.

    Raises:
        QuotaExhaustedError: If the allowance is used up.
    """
    if consumption.exhausted:
        raise QuotaExhaustedError(consumption.used, consumption.allowance)


class AllowanceResolver:
    """Answers what one tenant is allowed to spend.

    A separate object because the answer comes from two places and the
    precedence matters: a tenant's own allowance wins over the platform-wide
    default, so raising one business's cap does not move everybody's. Sharing it
    between adapters keeps that precedence from being re-decided per backend.
    """

    def __init__(self, settings: Settings, allowances: dict[str, float] | None = None) -> None:
        """Initialise the resolver.

        Args:
            settings: The harness settings holding the platform-wide default.
            allowances: Per-tenant overrides, or ``None`` when there are none.
        """
        self._settings = settings
        self._overrides = dict(allowances or {})

    def set_override(self, tenant: str, allowance: float | None) -> None:
        """Record or clear one tenant's own allowance.

        Args:
            tenant: The tenant whose allowance to set.
            allowance: What they may spend, or ``None`` to fall back to the
                platform default.
        """
        if allowance is None:
            self._overrides.pop(tenant, None)
            return
        self._overrides[tenant] = allowance

    def allowance_for(self, tenant: str) -> float:
        """Return what a tenant may spend.

        Args:
            tenant: The tenant to resolve an allowance for.

        Returns:
            The tenant's own allowance when they have one, otherwise the
            platform-wide default.
        """
        return self._overrides.get(tenant, self._settings.usage_allowance)


class InMemoryUsageLedger:
    """Holds ledger entries in a list, scoped by tenant on read.

    The fast suite's ledger and the single-worker default. It enforces the same
    check-before-call rule and prices calls through the same helpers as the
    Postgres ledger, so every behaviour except surviving a restart is exercised
    without a database.
    """

    def __init__(self, settings: Settings, allowances: dict[str, float] | None = None) -> None:
        """Initialise the empty ledger.

        Args:
            settings: The harness settings holding the rates and the default
                allowance.
            allowances: Per-tenant allowance overrides, or ``None`` for none.
        """
        self._settings = settings
        self._allowances = AllowanceResolver(settings, allowances)
        self._entries: list[LedgerEntry] = []

    def set_allowance(self, tenant: str, allowance: float | None) -> None:
        """Record or clear one tenant's own allowance.

        Args:
            tenant: The tenant whose allowance to set.
            allowance: What they may spend, or ``None`` for the platform default.
        """
        self._allowances.set_override(validate_tenant_id(tenant), allowance)

    def check(self, tenant: str) -> None:
        """Refuse the next billable call if the tenant's allowance is spent.

        Args:
            tenant: The tenant about to be charged.

        Raises:
            QuotaExhaustedError: If the tenant has used their whole allowance.
        """
        refuse_when_exhausted(self.consumption(tenant))

    def record(
        self,
        tenant: str,
        *,
        slug: str | None = None,
        stage_key: str | None = None,
        model: str = "",
        usage: Usage | None = None,
    ) -> LedgerEntry:
        """Append what one billable call cost, charged to its tenant.

        Args:
            tenant: The tenant to charge.
            slug: The campaign the call was made for, if any.
            stage_key: The pipeline stage the call belongs to, if any.
            model: The model identifier the provider billed for.
            usage: The token counts the call consumed.

        Returns:
            The stored entry, carrying the cost the ledger assigned it.
        """
        entry = build_entry(
            self._settings, validate_tenant_id(tenant), slug, stage_key, model, usage
        )
        self._entries.append(entry)
        return entry

    def consumption(self, tenant: str, slug: str | None = None) -> Consumption:
        """Report a tenant's spend against their allowance.

        Args:
            tenant: The tenant whose consumption to total.
            slug: One campaign to restrict the total to, or ``None`` for
                everything the tenant has spent.

        Returns:
            The report, including the per-campaign breakdown.
        """
        scoped = validate_tenant_id(tenant)
        owned = self._owned_by(scoped)
        counted = owned if slug is None else [entry for entry in owned if entry.slug == slug]
        return Consumption(
            tenant_id=scoped,
            used=total_of(counted),
            allowance=self._allowances.allowance_for(scoped),
            campaigns=per_campaign(owned),
        )

    def entries(self, tenant: str, slug: str | None = None) -> list[LedgerEntry]:
        """Return a tenant's ledger entries, newest first.

        Args:
            tenant: The tenant whose entries to read.
            slug: One campaign to restrict the entries to, or ``None`` for all.

        Returns:
            The entries, newest first, empty when nothing has been charged.
        """
        owned = self._owned_by(validate_tenant_id(tenant))
        if slug is not None:
            owned = [entry for entry in owned if entry.slug == slug]
        return list(reversed(owned))

    def _owned_by(self, tenant: str) -> list[LedgerEntry]:
        """Return the entries charged to one tenant, oldest first.

        Args:
            tenant: The validated tenant id.

        Returns:
            That tenant's entries; another tenant's are never included.
        """
        return [entry for entry in self._entries if entry.tenant_id == tenant]
