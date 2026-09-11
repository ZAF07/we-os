"""Postgres :class:`~marketing_os.ports.TenantDirectory` — where the IdP pairing lives.

This is the adapter the user's note is about: the Clerk Organization id belongs
in a column of the ``tenants`` table, paired with the business's name and the
platform's own ``tenant_id``, rather than serving as the identifier that every
document path, run row and checkpoint thread is partitioned by (ADR-0014).

The same row records the business's tier, once (ADR-0027): a fact the product
will bill on belongs in the platform's own table, not only in a vendor's
organization metadata. It also records when the business last reviewed its
Brand DNA (ADR-0028), the one timestamp both the Review item and the reminder
email are derived from — and, for that email, the address the business is
reached at and when it was last reminded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from marketing_os.adapters.tenants import (
    display_name_for,
    new_tenant_id,
    refuse_a_different_tier,
    validate_external_auth_id,
)
from marketing_os.errors import ToolError
from marketing_os.schemas import Tenant, TierName

TENANT_COLUMNS = (
    "tenant_id, name, external_auth_id, tier, dna_reviewed_at, contact_email, dna_reminded_at"
)


def _tenant_from_row(row: Any) -> Tenant:
    """Build a tenant from a row selected with :data:`TENANT_COLUMNS`.

    Args:
        row: The row, in column order.

    Returns:
        The tenant the row describes.
    """
    return Tenant(
        tenant_id=row[0],
        name=row[1],
        external_auth_id=row[2],
        tier=row[3],
        dna_reviewed_at=row[4],
        contact_email=row[5],
        dna_reminded_at=row[6],
    )


class PostgresTenantDirectory:
    """Registers businesses in the ``tenants`` table and resolves them by IdP id."""

    def __init__(self, pool: Any) -> None:
        """Initialise the directory.

        Args:
            pool: A ``psycopg_pool.ConnectionPool``.
        """
        self._pool = pool

    def resolve(
        self, *, external_auth_id: str, name: str | None = None, email: str | None = None
    ) -> Tenant:
        """Return the tenant for an IdP organization, registering it on first sight.

        A business's first authenticated request provisions its tenant; later
        requests find the same row, so renaming the organization in the IdP
        keeps the platform's copy current without disturbing ``tenant_id`` or
        the tier recorded on it. The signed-in email is recorded the same way:
        a request carrying one makes it the address the business is reached at,
        and a request carrying none leaves the recorded address alone.

        This runs on **every authenticated request**, so the common case — a
        known business whose name and address have not changed — is a read.
        Writing unconditionally would leave a dead row per request for the
        vacuum to clean up.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim.
            email: The signed-in email from the verified claim, if it carried one.

        Returns:
            The tenant that owns the business's data.

        Raises:
            ToolError: If the external id is empty.
        """
        cleaned = validate_external_auth_id(external_auth_id)
        display_name = display_name_for(cleaned, name)
        with self._pool.connection() as connection:
            row = connection.execute(
                f"SELECT {TENANT_COLUMNS} FROM tenants WHERE external_auth_id = %s",
                (cleaned,),
            ).fetchone()
            if row is not None and row[1] == display_name and (email is None or row[5] == email):
                return _tenant_from_row(row)
            row = connection.execute(
                "INSERT INTO tenants (tenant_id, name, external_auth_id, contact_email) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (external_auth_id) DO UPDATE SET name = EXCLUDED.name, "
                "contact_email = COALESCE(EXCLUDED.contact_email, tenants.contact_email) "
                f"RETURNING {TENANT_COLUMNS}",
                (new_tenant_id(), display_name, cleaned, email),
            ).fetchone()
        return _tenant_from_row(row)

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id.

        Returns:
            The tenant, or ``None`` when no tenant has that id.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                f"SELECT {TENANT_COLUMNS} FROM tenants WHERE tenant_id = %s",
                (tenant_id,),
            ).fetchone()
        if row is None:
            return None
        return _tenant_from_row(row)

    def all(self) -> list[Tenant]:
        """Return every registered tenant.

        Returns:
            The tenants, oldest registration first.
        """
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"SELECT {TENANT_COLUMNS} FROM tenants ORDER BY created_at, tenant_id"
            ).fetchall()
        return [_tenant_from_row(row) for row in rows]

    def set_tier(self, tenant_id: str, tier: TierName) -> Tenant:
        """Record a tenant's tier, once.

        The write is conditional on the column being empty, so two requests
        racing to record a first tier cannot both win: the second finds the
        row already filled and is judged against what it holds.

        Args:
            tenant_id: The platform tenant id.
            tier: The tier to record.

        Returns:
            The tenant, carrying the tier it now has recorded.

        Raises:
            TierAlreadySetError: If a different tier is already recorded.
            ToolError: If no tenant has that id.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                "UPDATE tenants SET tier = %s WHERE tenant_id = %s AND tier IS NULL "
                f"RETURNING {TENANT_COLUMNS}",
                (tier, tenant_id),
            ).fetchone()
            if row is not None:
                return _tenant_from_row(row)
            row = connection.execute(
                f"SELECT {TENANT_COLUMNS} FROM tenants WHERE tenant_id = %s",
                (tenant_id,),
            ).fetchone()
        if row is None:
            raise ToolError(f"No tenant '{tenant_id}' is registered.")
        return refuse_a_different_tier(_tenant_from_row(row), tier)

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
        with self._pool.connection() as connection:
            row = connection.execute(
                "UPDATE tenants SET dna_reviewed_at = %s WHERE tenant_id = %s "
                f"RETURNING {TENANT_COLUMNS}",
                (at, tenant_id),
            ).fetchone()
        if row is None:
            raise ToolError(f"No tenant '{tenant_id}' is registered.")
        return _tenant_from_row(row)

    def mark_dna_reminded(self, tenant_id: str, *, at: datetime) -> Tenant:
        """Record when a tenant was emailed that a review is due.

        Args:
            tenant_id: The platform tenant id.
            at: When the reminder was sent.

        Returns:
            The tenant, carrying the reminder it now has recorded.

        Raises:
            ToolError: If no tenant has that id.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                "UPDATE tenants SET dna_reminded_at = %s WHERE tenant_id = %s "
                f"RETURNING {TENANT_COLUMNS}",
                (at, tenant_id),
            ).fetchone()
        if row is None:
            raise ToolError(f"No tenant '{tenant_id}' is registered.")
        return _tenant_from_row(row)
