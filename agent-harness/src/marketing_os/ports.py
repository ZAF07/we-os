"""Ports — the interfaces the domain and orchestration depend on.

The model and tool ports are LangChain's own ``BaseChatModel`` and ``BaseTool``,
so they are not re-declared here. This module defines the remaining ports that
benefit from an explicit contract: the QA :class:`Reviewer`, which the graph
depends on, the :class:`DocumentStore`, which resolves where tenant documents
live (ADR-0014), the :class:`TenantDirectory`, which maps an identity provider's
organization onto the platform tenant that owns those documents, the
:class:`RunStore`, which holds run state durably so the one-active-run-per-campaign
guard survives a restart and spans workers, and the :class:`TokenVerifier`, which
establishes who a caller is (ADR-0013). Tests substitute all of them with
hermetic fakes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from marketing_os.schemas import ReviewVerdict, RunRecord, Tenant, VerifiedClaims


@runtime_checkable
class TokenVerifier(Protocol):
    """Establishes caller identity by verifying a bearer token's signature.

    The engine verifies tokens itself rather than trusting a frontend to have
    done so (ADR-0013), so reaching the engine directly cannot bypass tenancy.
    Implementations are IdP-agnostic: they hold an issuer and a key source, and
    no vendor SDK appears above this port.
    """

    def verify(self, token: str) -> VerifiedClaims:
        """Verify a bearer token and return the claims it carries.

        The result names the IdP's organization, not a platform tenant: mapping
        one to the other is the :class:`TenantDirectory`'s job, so no vendor
        identifier reaches a partition key.

        Args:
            token: The raw bearer token, without its ``Bearer `` prefix.

        Returns:
            The verified claims, including the organization the caller acts for.

        Raises:
            UnauthenticatedError: If the token is absent, malformed, expired,
                wrongly signed, issued for another issuer or audience, or
                carries no organization claim.
        """
        ...


@runtime_checkable
class DocumentStore(Protocol):
    """Tenant-scoped storage for the markdown documents the pipeline reads and writes.

    Documents are addressed by an explicit tenant plus a tenant-relative logical
    path — ``dna.md`` for the Brand DNA, ``campaigns/<slug>/<name>.md`` for
    campaign documents. Markdown stays the agent I/O format; adapters decide
    only where a document physically lives.
    """

    def read(self, tenant: str, path: str) -> str:
        """Return a document's text.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            The document content.

        Raises:
            DocumentNotFoundError: If no such document exists for the tenant.
        """
        ...

    def write(self, tenant: str, path: str, content: str) -> None:
        """Create or replace a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.
            content: The full document text.
        """
        ...

    def exists(self, tenant: str, path: str) -> bool:
        """Return whether a document exists.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            ``True`` if the document exists for the tenant.
        """
        ...

    def list(self, tenant: str, prefix: str) -> list[str]:
        """List the documents under a logical directory prefix.

        Args:
            tenant: The tenant whose documents are listed.
            prefix: The logical directory to list, for example ``campaigns/<slug>``.

        Returns:
            The sorted tenant-relative paths of every document under the prefix.
        """
        ...

    def describe(self, tenant: str, path: str) -> str:
        """Return a human-readable location for a document, for error messages.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            A location string an operator can act on (for the filesystem
            adapter, the absolute path).
        """
        ...


@runtime_checkable
class Reviewer(Protocol):
    """A QA judge that scores a deliverable against a stage rubric."""

    async def areview(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Judge a deliverable against the rubric for its stage.

        The review runs as an awaited coroutine (per ADR-0009) so the review
        node's LLM call is on the event loop and aborts when the run is cancelled.

        Args:
            stage_key: The pipeline stage the deliverable belongs to.
            deliverable_text: The full text of the deliverable to review.

        Returns:
            A structured :class:`ReviewVerdict` with the pass/fail decision and
            any discrepancies to resolve.
        """
        ...


@runtime_checkable
class TenantDirectory(Protocol):
    """Maps an identity provider's organization onto the platform tenant that owns data.

    The IdP's identifier for a business (for Clerk, the Organization
    ``org_...``) is a vendor detail: it changes when the IdP is swapped or an
    organization is re-created, and it belongs in one column rather than in
    every document path, run row and checkpoint thread. The directory is the one
    place that translation happens, so ``tenant_id`` everywhere else is
    platform-owned (ADR-0014).
    """

    def resolve(self, *, external_auth_id: str, name: str | None = None) -> Tenant:
        """Return the tenant for an IdP organization, registering it on first sight.

        Args:
            external_auth_id: The IdP's identifier for the business.
            name: The business's display name from the verified claim, used when
                the tenant is registered and to keep the recorded name current.

        Returns:
            The tenant that owns the business's data.
        """
        ...

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by its platform id.

        Args:
            tenant_id: The platform tenant id.

        Returns:
            The tenant, or ``None`` when no tenant has that id.
        """
        ...


@runtime_checkable
class RunStore(Protocol):
    """Durable, shared record of run state and the one-active-run-per-campaign claim.

    Claiming is the load-bearing operation: it must be atomic across processes,
    because the guard's whole purpose is stopping two runs from writing the same
    campaign's deliverables. Every read is tenant-scoped for the same reason the
    :class:`DocumentStore`'s is — a run id belonging to another business must be
    unfindable, not merely refused (ADR-0013).
    """

    def claim(self, record: RunRecord) -> RunRecord:
        """Claim a campaign for a run, refusing a second concurrent claim.

        Args:
            record: The run to record as running.

        Returns:
            The stored record.

        Raises:
            RunConflictError: If the campaign already has a running run.
        """
        ...

    def finish(self, run_id: str, status: str) -> None:
        """Record a run's terminal status, releasing its campaign claim.

        A run already resolved (cancelled from another worker, or reclaimed
        after a restart) keeps the status it was given, so a late callback
        cannot resurrect it.

        Args:
            run_id: The run to resolve.
            status: The terminal status to record.
        """
        ...

    def get(self, run_id: str, tenant: str) -> RunRecord | None:
        """Return a tenant's run by id.

        Args:
            run_id: The run id to look up.
            tenant: The tenant the caller acts for.

        Returns:
            The record, or ``None`` when no run has that id **or** it belongs to
            another tenant.
        """
        ...

    def active(self, tenant: str) -> list[RunRecord]:
        """Return one tenant's currently running runs.

        Args:
            tenant: The tenant whose runs to list.

        Returns:
            The tenant's running records, one per busy campaign.
        """
        ...

    def active_for_campaign(self, tenant: str, slug: str) -> RunRecord | None:
        """Return the running run holding a campaign's claim.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The claiming record, or ``None`` when the campaign is idle.
        """
        ...

    def heartbeat(self, run_ids: list[str], now: float) -> None:
        """Report that runs are still executing on their owning worker.

        Args:
            run_ids: The runs this worker is still executing.
            now: The current UTC epoch timestamp.
        """
        ...

    def reclaim_stale(self, *, now: float, stale_after: float, status: str) -> list[RunRecord]:
        """Resolve runs whose owning worker stopped reporting them alive.

        This is what a restarted process calls so runs its predecessor was
        executing get a terminal status instead of staying ``running`` forever.
        A run whose worker is still heartbeating it is not stale, so it is left
        alone and a restart cannot kill another worker's work.

        Args:
            now: The current UTC epoch timestamp.
            stale_after: How many seconds without a heartbeat mark a run
                abandoned.
            status: The terminal status to record for abandoned runs.

        Returns:
            The records that were resolved.
        """
        ...
