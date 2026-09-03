"""Postgres :class:`~marketing_os.ports.UsageLedger` — the production ledger.

Holds the same append-only entries as the in-memory ledger and prices calls
through the same helpers, so it passes the same conformance suite and no caller
can tell which store is behind the port (ADR-0020). Two things it alone
provides: the record of what a tenant spent survives a restart, and totals are
summed by the database rather than by pulling every row into the process — which
matters because the ledger grows for the life of the account while the answer it
gives is one number.

The per-tenant allowance lives on the ``tenants`` row rather than in a table of
its own: it is a fact about the business, of which there is exactly one.

Every operation opens one transaction and sets the tenant for it before
querying, exactly as the document and deliverable adapters do — the ``SET`` is
what the ``usage_ledger_tenant_isolation`` row-level-security policy checks, so a
query that somehow lost its ``tenant_id`` predicate still returns nothing across
tenants.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from marketing_os.adapters.documents import validate_tenant_id
from marketing_os.adapters.postgres.schema import TENANT_SETTING
from marketing_os.adapters.usage import build_entry, rank_campaigns, refuse_when_exhausted
from marketing_os.config import Settings
from marketing_os.schemas import Consumption, LedgerEntry, Usage

_COLUMNS = "tenant_id, slug, stage_key, kind, model, units, cost, recorded_at"


def _to_entry(row: tuple[Any, ...]) -> LedgerEntry:
    """Build a :class:`LedgerEntry` from a selected row.

    Args:
        row: A row selected with :data:`_COLUMNS`, in that column order.

    Returns:
        The entry the row records.
    """
    return LedgerEntry(
        tenant_id=str(row[0]),
        slug=row[1],
        stage_key=row[2],
        kind=str(row[3]),
        model=str(row[4]),
        units=int(row[5]),
        cost=float(row[6]),
        recorded_at=row[7].isoformat(),
    )


class PostgresUsageLedger:
    """Serves each tenant's spend from ``usage_ledger``, and their allowance from ``tenants``."""

    def __init__(self, pool: Any, settings: Settings) -> None:
        """Initialise the ledger.

        Args:
            pool: A ``psycopg_pool.ConnectionPool`` whose connections belong to
                the application role (not a superuser, which bypasses RLS).
            settings: The harness settings holding the per-model token rates and
                the platform-wide default allowance.
        """
        self._pool = pool
        self._settings = settings

    @contextmanager
    def _scoped_to(self, tenant: str) -> Iterator[tuple[Any, str]]:
        """Open a transaction that may only touch one tenant's rows.

        Args:
            tenant: The tenant every statement in the transaction may touch.

        Yields:
            The open connection and the validated tenant id.

        Raises:
            ToolError: If the tenant id is malformed.
        """
        scoped_tenant = validate_tenant_id(tenant)
        with self._pool.connection() as connection:
            connection.execute("SELECT set_config(%s, %s, true)", (TENANT_SETTING, scoped_tenant))
            yield connection, scoped_tenant

    def set_allowance(self, tenant: str, allowance: float | None) -> None:
        """Record or clear one tenant's own allowance.

        Writes onto the tenant's existing row, so a tenant the directory has not
        registered is left alone rather than conjured into existence by a
        billing operation.

        Args:
            tenant: The tenant whose allowance to set.
            allowance: What they may spend, or ``None`` to fall back to the
                platform-wide default.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            connection.execute(
                "UPDATE tenants SET allowance = %s WHERE tenant_id = %s",
                (allowance, scoped),
            )

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
        with self._scoped_to(tenant) as (connection, scoped):
            entry = build_entry(self._settings, scoped, slug, stage_key, model, usage)
            row = connection.execute(
                "INSERT INTO usage_ledger "
                "(tenant_id, slug, stage_key, kind, model, units, cost) "
                f"VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING {_COLUMNS}",
                (
                    scoped,
                    entry.slug,
                    entry.stage_key,
                    entry.kind,
                    entry.model,
                    entry.units,
                    entry.cost,
                ),
            ).fetchone()
        return _to_entry(row)

    def consumption(self, tenant: str, slug: str | None = None) -> Consumption:
        """Report a tenant's spend against their allowance.

        The totals are summed in the database rather than over fetched rows: the
        ledger grows for the life of the account, and the answer is one number.

        Args:
            tenant: The tenant whose consumption to total.
            slug: One campaign to restrict the total to, or ``None`` for
                everything the tenant has spent.

        Returns:
            The report, including the per-campaign breakdown.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            if slug is None:
                used = connection.execute(
                    "SELECT COALESCE(SUM(cost), 0) FROM usage_ledger WHERE tenant_id = %s",
                    (scoped,),
                ).fetchone()[0]
            else:
                used = connection.execute(
                    "SELECT COALESCE(SUM(cost), 0) FROM usage_ledger "
                    "WHERE tenant_id = %s AND slug = %s",
                    (scoped, slug),
                ).fetchone()[0]
            breakdown = connection.execute(
                "SELECT slug, SUM(cost) FROM usage_ledger "
                "WHERE tenant_id = %s AND slug IS NOT NULL GROUP BY slug",
                (scoped,),
            ).fetchall()
            override = connection.execute(
                "SELECT allowance FROM tenants WHERE tenant_id = %s",
                (scoped,),
            ).fetchone()
        allowance = self._settings.usage_allowance
        if override is not None and override[0] is not None:
            allowance = float(override[0])
        return Consumption(
            tenant_id=scoped,
            used=float(used),
            allowance=allowance,
            campaigns=rank_campaigns({str(row[0]): float(row[1]) for row in breakdown}),
        )

    def entries(self, tenant: str, slug: str | None = None) -> list[LedgerEntry]:
        """Return a tenant's ledger entries, newest first.

        Args:
            tenant: The tenant whose entries to read.
            slug: One campaign to restrict the entries to, or ``None`` for all.

        Returns:
            The entries, newest first, empty when nothing has been charged.
        """
        with self._scoped_to(tenant) as (connection, scoped):
            if slug is None:
                rows = connection.execute(
                    f"SELECT {_COLUMNS} FROM usage_ledger WHERE tenant_id = %s "
                    "ORDER BY sequence DESC",
                    (scoped,),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT {_COLUMNS} FROM usage_ledger "
                    "WHERE tenant_id = %s AND slug = %s ORDER BY sequence DESC",
                    (scoped, slug),
                ).fetchall()
        return [_to_entry(row) for row in rows]
