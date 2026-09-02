"""Postgres :class:`~marketing_os.ports.RunStore` — the shared run claim.

The whole reason this adapter exists is the partial unique index
``runs_one_active_per_campaign``: it makes "one active run per campaign" a
constraint the database enforces rather than a check a call site can forget.
:meth:`PostgresRunStore.claim` does not check-then-insert — it inserts and lets
the index refuse the second claim, because a check followed by an insert is a
race two simultaneous requests would lose.
"""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.runs import RUNNING
from marketing_os.errors import RunConflictError
from marketing_os.schemas import RunRecord

_COLUMNS = "run_id, tenant_id, user_id, slug, stage, status, started_at"
_IS_RUNNING = f"status = '{RUNNING}'"


def _to_record(row: Any) -> RunRecord:
    """Build a run record from a ``runs`` row selected with :data:`_COLUMNS`.

    Args:
        row: The selected row.

    Returns:
        The run record it describes.
    """
    return RunRecord(
        run_id=row[0],
        tenant_id=row[1],
        user_id=row[2],
        slug=row[3],
        stage=row[4],
        status=row[5],
        started_at=row[6],
    )


class PostgresRunStore:
    """Holds run claims and lifecycle statuses in the ``runs`` table."""

    def __init__(self, pool: Any) -> None:
        """Initialise the store.

        Args:
            pool: A ``psycopg_pool.ConnectionPool``.
        """
        self._pool = pool

    def claim(self, record: RunRecord) -> RunRecord:
        """Claim a campaign for a run, refusing a second concurrent claim.

        Args:
            record: The run to record as running.

        Returns:
            The stored record.

        Raises:
            RunConflictError: If the campaign already has a running run.
        """
        claimed = record.model_copy(update={"status": RUNNING})
        with self._pool.connection() as connection:
            inserted = connection.execute(
                f"INSERT INTO runs ({_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING "
                f"RETURNING {_COLUMNS}",
                (
                    claimed.run_id,
                    claimed.tenant_id,
                    claimed.user_id,
                    claimed.slug,
                    claimed.stage,
                    claimed.status,
                    claimed.started_at,
                ),
            ).fetchone()
        if inserted is not None:
            return _to_record(inserted)
        held = self.active_for_campaign(record.tenant_id, record.slug)
        if held is None:
            raise RunConflictError(record.slug, record.run_id)
        raise RunConflictError(record.slug, held.run_id, held.user_id)

    def finish(self, run_id: str, status: str) -> None:
        """Record a run's terminal status, releasing its campaign claim.

        The ``status = 'running'`` predicate is what stops a late callback from
        overwriting a run that was already cancelled or reclaimed.

        Args:
            run_id: The run to resolve.
            status: The terminal status to record.
        """
        with self._pool.connection() as connection:
            connection.execute(
                f"UPDATE runs SET status = %s WHERE run_id = %s AND {_IS_RUNNING}",
                (status, run_id),
            )

    def get(self, run_id: str, tenant: str) -> RunRecord | None:
        """Return a tenant's run by id.

        Args:
            run_id: The run id to look up.
            tenant: The tenant the caller acts for.

        Returns:
            The record, or ``None`` when no run has that id **or** it belongs to
            another tenant.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM runs WHERE run_id = %s AND tenant_id = %s",
                (run_id, tenant),
            ).fetchone()
        return None if row is None else _to_record(row)

    def active(self, tenant: str) -> list[RunRecord]:
        """Return one tenant's currently running runs.

        Args:
            tenant: The tenant whose runs to list.

        Returns:
            The tenant's running records, one per busy campaign.
        """
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM runs WHERE tenant_id = %s AND {_IS_RUNNING} "
                "ORDER BY started_at",
                (tenant,),
            ).fetchall()
        return [_to_record(row) for row in rows]

    def active_for_campaign(self, tenant: str, slug: str) -> RunRecord | None:
        """Return the running run holding a campaign's claim.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The claiming record, or ``None`` when the campaign is idle.
        """
        with self._pool.connection() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM runs WHERE tenant_id = %s AND slug = %s AND {_IS_RUNNING}",
                (tenant, slug),
            ).fetchone()
        return None if row is None else _to_record(row)

    def for_campaign(self, tenant: str, slug: str) -> list[RunRecord]:
        """Return every run recorded for a campaign, newest first.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The campaign's runs whatever their status.
        """
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM runs "
                "WHERE tenant_id = %s AND slug = %s ORDER BY started_at DESC",
                (tenant, slug),
            ).fetchall()
        return [_to_record(row) for row in rows]

    def reclaim_running(self, status: str) -> list[RunRecord]:
        """Resolve every run still marked running, and return them.

        Args:
            status: The terminal status to record for the abandoned runs.

        Returns:
            The records that were resolved.
        """
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"UPDATE runs SET status = %s WHERE {_IS_RUNNING} RETURNING {_COLUMNS}",
                (status,),
            ).fetchall()
        return [_to_record(row) for row in rows]
