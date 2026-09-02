"""Postgres :class:`~marketing_os.ports.RunStore` — the shared run claim.

The whole reason this adapter exists is the partial unique index
``runs_one_active_per_campaign``: it makes "one active run per campaign" a
constraint the database enforces, so the guard holds when the service runs more
than one worker. :meth:`PostgresRunStore.claim` does not check-then-insert —
it inserts and lets the index refuse the second claim, because a check followed
by an insert is exactly the race two workers would lose.
"""

from __future__ import annotations

from typing import Any

from marketing_os.adapters.runs import RUNNING
from marketing_os.errors import RunConflictError
from marketing_os.schemas import RunRecord

_COLUMNS = "run_id, tenant_id, slug, stage, status, worker_id, started_at, heartbeat_at"
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
        slug=row[2],
        stage=row[3],
        status=row[4],
        worker_id=row[5],
        started_at=row[6],
        heartbeat_at=row[7],
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
                f"INSERT INTO runs ({_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING "
                f"RETURNING {_COLUMNS}",
                (
                    claimed.run_id,
                    claimed.tenant_id,
                    claimed.slug,
                    claimed.stage,
                    claimed.status,
                    claimed.worker_id,
                    claimed.started_at,
                    claimed.heartbeat_at,
                ),
            ).fetchone()
        if inserted is not None:
            return _to_record(inserted)
        held = self.active_for_campaign(record.tenant_id, record.slug)
        raise RunConflictError(record.slug, held.run_id if held else record.run_id)

    def finish(self, run_id: str, status: str) -> None:
        """Record a run's terminal status, releasing its campaign claim.

        The ``status = 'running'`` predicate is what stops a late callback from
        overwriting a run another worker already cancelled or reclaimed.

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

    def heartbeat(self, run_ids: list[str], now: float) -> None:
        """Report that runs are still executing on their owning worker.

        Args:
            run_ids: The runs this worker is still executing.
            now: The current UTC epoch timestamp.
        """
        if not run_ids:
            return
        with self._pool.connection() as connection:
            connection.execute(
                f"UPDATE runs SET heartbeat_at = %s WHERE run_id = ANY(%s) AND {_IS_RUNNING}",
                (now, list(run_ids)),
            )

    def reclaim_stale(self, *, now: float, stale_after: float, status: str) -> list[RunRecord]:
        """Resolve runs whose owning worker stopped reporting them alive.

        Args:
            now: The current UTC epoch timestamp.
            stale_after: How many seconds without a heartbeat mark a run abandoned.
            status: The terminal status to record for abandoned runs.

        Returns:
            The records that were resolved.
        """
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"UPDATE runs SET status = %s WHERE {_IS_RUNNING} AND heartbeat_at <= %s "
                f"RETURNING {_COLUMNS}",
                (status, now - stale_after),
            ).fetchall()
        return [_to_record(row) for row in rows]
