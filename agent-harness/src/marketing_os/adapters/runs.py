"""Run store adapters — where the one-active-run-per-campaign claim is held.

Implements the :class:`~marketing_os.ports.RunStore` port. The claim is the
point: two runs of the same campaign write the same deliverable documents, so
the guard must be atomic. Holding it in a dict makes it atomic within one
process; holding it in Postgres (see :mod:`marketing_os.adapters.postgres.runs`)
makes it atomic across every worker, which is what lets the service run more
than one.

The store also carries each run's lifecycle status, so a status query no longer
depends on a JSONL trace being on the same machine that ran it, and a restarted
process can resolve the runs its predecessor was executing rather than leaving
them ``running`` forever.
"""

from __future__ import annotations

from marketing_os.errors import RunConflictError
from marketing_os.schemas import RunRecord

RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"


class InMemoryRunStore:
    """Holds run records in a dict, keyed by run id; nothing is shared between processes.

    This is the fast suite's store and the single-worker default. It enforces
    the same claim rule as the Postgres store, so every behaviour except
    cross-process sharing is exercised without a database.
    """

    def __init__(self) -> None:
        """Initialise the empty store."""
        self._records: dict[str, RunRecord] = {}

    def claim(self, record: RunRecord) -> RunRecord:
        """Claim a campaign for a run, refusing a second concurrent claim.

        Args:
            record: The run to record as running.

        Returns:
            The stored record.

        Raises:
            RunConflictError: If the campaign already has a running run.
        """
        held = self.active_for_campaign(record.tenant_id, record.slug)
        if held is not None:
            raise RunConflictError(record.slug, held.run_id)
        stored = record.model_copy(update={"status": RUNNING})
        self._records[stored.run_id] = stored
        return stored

    def finish(self, run_id: str, status: str) -> None:
        """Record a run's terminal status, releasing its campaign claim.

        Args:
            run_id: The run to resolve.
            status: The terminal status to record.
        """
        record = self._records.get(run_id)
        if record is None or record.status != RUNNING:
            return
        self._records[run_id] = record.model_copy(update={"status": status})

    def get(self, run_id: str, tenant: str) -> RunRecord | None:
        """Return a tenant's run by id.

        Args:
            run_id: The run id to look up.
            tenant: The tenant the caller acts for.

        Returns:
            The record, or ``None`` when no run has that id **or** it belongs to
            another tenant.
        """
        record = self._records.get(run_id)
        if record is None or record.tenant_id != tenant:
            return None
        return record

    def active(self, tenant: str) -> list[RunRecord]:
        """Return one tenant's currently running runs.

        Args:
            tenant: The tenant whose runs to list.

        Returns:
            The tenant's running records, one per busy campaign.
        """
        return [
            record
            for record in self._records.values()
            if record.tenant_id == tenant and record.status == RUNNING
        ]

    def active_for_campaign(self, tenant: str, slug: str) -> RunRecord | None:
        """Return the running run holding a campaign's claim.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The claiming record, or ``None`` when the campaign is idle.
        """
        for record in self._records.values():
            if record.tenant_id == tenant and record.slug == slug and record.status == RUNNING:
                return record
        return None

    def heartbeat(self, run_ids: list[str], now: float) -> None:
        """Report that runs are still executing on their owning worker.

        Args:
            run_ids: The runs this worker is still executing.
            now: The current UTC epoch timestamp.
        """
        for run_id in run_ids:
            record = self._records.get(run_id)
            if record is not None and record.status == RUNNING:
                self._records[run_id] = record.model_copy(update={"heartbeat_at": now})

    def reclaim_stale(self, *, now: float, stale_after: float, status: str) -> list[RunRecord]:
        """Resolve runs whose owning worker stopped reporting them alive.

        Args:
            now: The current UTC epoch timestamp.
            stale_after: How many seconds without a heartbeat mark a run abandoned.
            status: The terminal status to record for abandoned runs.

        Returns:
            The records that were resolved.
        """
        cutoff = now - stale_after
        reclaimed: list[RunRecord] = []
        for run_id, record in list(self._records.items()):
            if record.status != RUNNING or record.heartbeat_at > cutoff:
                continue
            resolved = record.model_copy(update={"status": status})
            self._records[run_id] = resolved
            reclaimed.append(resolved)
        return reclaimed
