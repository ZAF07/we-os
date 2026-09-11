"""Tenant directory adapters — who owns the data an identity claim points at.

Implements the :class:`~marketing_os.ports.TenantDirectory` port (ADR-0014). The
identity provider names a business with its own identifier — Clerk issues an
Organization id such as ``org_3IlR...`` — and that identifier is a vendor
detail. Writing it into every document path, run row and checkpoint thread welds
the platform's partition key to one IdP account, so the directory translates it
once into a platform-owned ``tenant_id`` and records the pairing.

Two adapters, matching where documents live. The Postgres adapter (see
:mod:`marketing_os.adapters.postgres.tenants`) mints platform ids and stores the
external id beside the business name. The passthrough adapter is for the
filesystem layer, where a tenant *is* a directory name and there is no table to
mint an id in: it reports the external id as the tenant id, which is exactly the
pre-Postgres behaviour it preserves.

The directory also records a business's **tier**, once (ADR-0027), and when
it last **reviewed its Brand DNA** (ADR-0028). Both are the platform's own
record rather than the identity provider's, so they live on the tenant row
beside the pairing — which is why the passthrough adapter, having no row, holds
neither.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from marketing_os.errors import TierAlreadySetError, ToolError
from marketing_os.schemas import Tenant, TierName

TENANT_ID_PREFIX = "ten_"


def new_tenant_id() -> str:
    """Mint a fresh platform tenant id.

    Returns:
        A ``ten_``-prefixed identifier owned by the platform, unrelated to any
        identity provider's naming.
    """
    return f"{TENANT_ID_PREFIX}{uuid4().hex}"


def display_name_for(external_auth_id: str, name: str | None) -> str:
    """Return the name to record for a business.

    Args:
        external_auth_id: The IdP's identifier for the business.
        name: The display name from the verified claim, if the token carried one.

    Returns:
        The claim's name when present, otherwise the external id, so a tenant is
        never nameless.
    """
    cleaned = (name or "").strip()
    return cleaned or external_auth_id


def validate_external_auth_id(external_auth_id: str) -> str:
    """Validate an identity provider's organization identifier.

    Args:
        external_auth_id: The identifier read from the verified organization claim.

    Returns:
        The identifier, stripped of surrounding whitespace.

    Raises:
        ToolError: If the identifier is empty.
    """
    cleaned = external_auth_id.strip()
    if not cleaned:
        raise ToolError("An identity claim carried no organization id.")
    return cleaned


def refuse_a_different_tier(tenant: Tenant, tier: TierName) -> Tenant:
    """Return a tenant whose recorded tier is the one asked for, or refuse.

    The set-once judgement the minting directories share once their write
    found the tier already filled: the same tier again is harmless — the
    welcome flow's retry depends on it — and a different one is the typed
    refusal (ADR-0027).

    Args:
        tenant: The tenant as recorded.
        tier: The tier asked for.

    Returns:
        The tenant, unchanged.

    Raises:
        TierAlreadySetError: If the tenant records a different tier.
    """
    if tenant.tier is not None and tenant.tier != tier:
        raise TierAlreadySetError(tenant.tier, tier)
    return tenant


class PassthroughTenantDirectory:
    """Reports the IdP's organization id as the tenant id, for the filesystem layer.

    Local development and the CLI resolve documents from ``tenants/<tenant>/``,
    where the directory name *is* the tenant id and there is no table to mint a
    platform id in. Minting one here would orphan every existing directory, so
    this adapter keeps the identifiers identical and defers the split to the
    Postgres deployment, where the external id gets its own column.
    """

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Return the tenant for an IdP organization, named after itself.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.

        Returns:
            A tenant whose ``tenant_id`` and ``external_auth_id`` are the same value.

        Raises:
            ToolError: If the external id is empty.
        """
        cleaned = validate_external_auth_id(external_auth_id)
        return Tenant(
            tenant_id=cleaned,
            name=display_name_for(cleaned, name),
            external_auth_id=cleaned,
        )

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id, which here is the external id.

        Returns:
            The tenant, or ``None`` when the id is empty.
        """
        cleaned = tenant_id.strip()
        if not cleaned:
            return None
        return _tenant_named_after_itself(cleaned)

    def set_tier(self, tenant_id: str, tier: TierName) -> Tenant:
        """Accept a tier for a tenant, and keep none of it.

        The filesystem layer has no table to hold a tier in, so nothing is
        recorded and the tenant keeps reporting no tier. The call is accepted
        rather than refused so the flow that records a tier does not fail on the
        one layer that cannot keep it.

        Args:
            tenant_id: The platform tenant id, which here is the external id.
            tier: The tier asked for, which is not retained.

        Returns:
            The tenant, still carrying no tier.

        Raises:
            ToolError: If the tenant id is empty.
        """
        cleaned = validate_external_auth_id(tenant_id)
        return _tenant_named_after_itself(cleaned)

    def mark_dna_reviewed(self, tenant_id: str, *, at: datetime) -> Tenant:
        """Accept a review for a tenant, and keep none of it.

        As with the tier: the filesystem layer has no row to hold a timestamp
        in, so nothing is recorded and the tenant keeps reporting no review.
        Accepted rather than refused so the DNA writes that count as a review
        do not fail on the one layer that cannot keep one. The consequence is
        stated plainly: on this layer a due review counts from when the
        answers were last saved and the Reviewed action cannot clear it. No
        deployment serves this layer — the API refuses to start without
        Postgres — so only the CLI and the test suite ever see it.

        Args:
            tenant_id: The platform tenant id, which here is the external id.
            at: When the review happened, which is not retained.

        Returns:
            The tenant, still carrying no review.

        Raises:
            ToolError: If the tenant id is empty.
        """
        cleaned = validate_external_auth_id(tenant_id)
        return _tenant_named_after_itself(cleaned)


def _tenant_named_after_itself(tenant_id: str) -> Tenant:
    """Build the tenant the passthrough directory reports for an id.

    Args:
        tenant_id: The id, already validated, which is also the name and the
            external id on this layer.

    Returns:
        A tenant with no tier and no review, since there is no row to keep them.
    """
    return Tenant(tenant_id=tenant_id, name=tenant_id, external_auth_id=tenant_id)


class InMemoryTenantDirectory:
    """Mints platform tenant ids and holds the pairings in a dict.

    Behaves exactly as the Postgres directory does — a first sighting registers
    a tenant under a fresh platform id, a later one returns the same tenant and
    refreshes its recorded name — so tests can exercise the real translation
    without a database.
    """

    def __init__(self) -> None:
        """Initialise the empty directory."""
        self._by_external: dict[str, Tenant] = {}
        self._by_tenant: dict[str, Tenant] = {}

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Return the tenant for an IdP organization, registering it on first sight.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.

        Returns:
            The tenant that owns the business's data.

        Raises:
            ToolError: If the external id is empty.
        """
        cleaned = validate_external_auth_id(external_auth_id)
        existing = self._by_external.get(cleaned)
        tenant = Tenant(
            tenant_id=existing.tenant_id if existing else new_tenant_id(),
            name=display_name_for(cleaned, name),
            external_auth_id=cleaned,
            tier=existing.tier if existing else None,
            dna_reviewed_at=existing.dna_reviewed_at if existing else None,
        )
        self._remember(tenant)
        return tenant

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id.

        Returns:
            The tenant, or ``None`` when no tenant has that id.
        """
        return self._by_tenant.get(tenant_id)

    def set_tier(self, tenant_id: str, tier: TierName) -> Tenant:
        """Record a tenant's tier, once.

        Args:
            tenant_id: The platform tenant id.
            tier: The tier to record.

        Returns:
            The tenant, carrying the tier it now has recorded.

        Raises:
            TierAlreadySetError: If a different tier is already recorded.
            ToolError: If no tenant has that id.
        """
        existing = self._by_tenant.get(tenant_id)
        if existing is None:
            raise ToolError(f"No tenant '{tenant_id}' is registered.")
        if existing.tier is not None:
            return refuse_a_different_tier(existing, tier)
        tenant = existing.model_copy(update={"tier": tier})
        self._remember(tenant)
        return tenant

    def mark_dna_reviewed(self, tenant_id: str, *, at: datetime) -> Tenant:
        """Record when a tenant reviewed its Brand DNA.

        Args:
            tenant_id: The platform tenant id.
            at: When the review happened.

        Returns:
            The tenant, carrying the review it now has recorded.

        Raises:
            ToolError: If no tenant has that id.
        """
        existing = self._by_tenant.get(tenant_id)
        if existing is None:
            raise ToolError(f"No tenant '{tenant_id}' is registered.")
        tenant = existing.model_copy(update={"dna_reviewed_at": at})
        self._remember(tenant)
        return tenant

    def _remember(self, tenant: Tenant) -> None:
        """Index a tenant by both of its identifiers.

        Args:
            tenant: The tenant to hold.
        """
        self._by_external[tenant.external_auth_id] = tenant
        self._by_tenant[tenant.tenant_id] = tenant
