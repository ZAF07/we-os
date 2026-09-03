"""Run store adapters — where the one-active-run-per-campaign claim is held.

Implements the :class:`~marketing_os.ports.RunStore` port. The claim is the
point: two runs of the same campaign write the same deliverable documents, so a
second one is refused — including when it comes from a colleague in the same
business, since two people driving one campaign would overwrite each other's
work.

The store also carries each run's lifecycle status, so a status outlives the
process that produced it and a restart can resolve the runs it was holding
rather than leaving them ``running`` forever.

``awaiting_approval`` is the one non-terminal status besides ``running``: a run
halted at an Approval Gate is not finished and has not failed, it is waiting on a
person (ADR-0015, ADR-0017). It **keeps its campaign claim**, because the person
approving it is going to resume this run and nobody else may start a competing
one in the meantime — which is what ``LIVE_STATUSES`` names: the statuses that
still hold a claim.
"""

from __future__ import annotations

from marketing_os.errors import RunConflictError, ValidationError
from marketing_os.schemas import RunRecord

RUNNING = "running"
AWAITING_APPROVAL = "awaiting_approval"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"
LIVE_STATUSES = (RUNNING, AWAITING_APPROVAL)


def validate_live_status(status: str) -> str:
    """Return a status that still holds a campaign claim, refusing any other.

    The claim index covers exactly the live statuses, so writing anything else
    through :meth:`set_live_status` would free the campaign for a competing run without
    anyone intending it. Checking here means every adapter refuses the same
    values rather than each one trusting its caller.

    Args:
        status: The status a caller wants to hold a live run at.

    Returns:
        The status, unchanged.

    Raises:
        ValidationError: If the status is not one that holds a claim.
    """
    if status not in LIVE_STATUSES:
        raise ValidationError(
            f"'{status}' is not a live run status. Use one of: {', '.join(LIVE_STATUSES)}."
        )
    return status


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
            raise RunConflictError(record.slug, held.run_id, held.user_id)
        stored = record.model_copy(update={"status": RUNNING})
        self._records[stored.run_id] = stored
        return stored

    def set_live_status(self, run_id: str, status: str) -> RunRecord | None:
        """Move a live run between the non-terminal statuses, keeping its claim.

        Args:
            run_id: The run to move.
            status: The non-terminal status to record.

        Returns:
            The updated record, or ``None`` when the run is already resolved.

        Raises:
            ValidationError: If the status is not one that holds a claim.
        """
        held_status = validate_live_status(status)
        record = self._records.get(run_id)
        if record is None or record.status not in LIVE_STATUSES:
            return None
        held = record.model_copy(update={"status": held_status})
        self._records[run_id] = held
        return held

    def finish(self, run_id: str, status: str) -> None:
        """Record a run's terminal status, releasing its campaign claim.

        Args:
            run_id: The run to resolve.
            status: The terminal status to record.
        """
        record = self._records.get(run_id)
        if record is None or record.status not in LIVE_STATUSES:
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
            The tenant's live records, one per busy campaign — including runs
            halted at an Approval Gate, which still hold their campaign.
        """
        return [
            record
            for record in self._records.values()
            if record.tenant_id == tenant and record.status in LIVE_STATUSES
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
            if (
                record.tenant_id == tenant
                and record.slug == slug
                and record.status in LIVE_STATUSES
            ):
                return record
        return None

    def for_campaign(self, tenant: str, slug: str) -> list[RunRecord]:
        """Return every run recorded for a campaign, newest first.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The campaign's runs whatever their status.
        """
        matching = [
            record
            for record in self._records.values()
            if record.tenant_id == tenant and record.slug == slug
        ]
        return sorted(matching, key=lambda record: record.started_at, reverse=True)

    def reclaim_running(self, status: str) -> list[RunRecord]:
        """Resolve every run still marked running, and return them.

        A run halted at an Approval Gate is deliberately left alone: it is not
        mid-execution, it is waiting on a person, and its state is durably
        checkpointed. Sweeping it would mean a deploy silently discarded work
        the owner was about to approve (ADR-0015).

        Args:
            status: The terminal status to record for the abandoned runs.

        Returns:
            The records that were resolved.
        """
        reclaimed: list[RunRecord] = []
        for run_id, record in list(self._records.items()):
            if record.status != RUNNING:
                continue
            resolved = record.model_copy(update={"status": status})
            self._records[run_id] = resolved
            reclaimed.append(resolved)
        return reclaimed
