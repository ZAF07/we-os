"""Ports — the interfaces the domain and orchestration depend on.

The model and tool ports are LangChain's own ``BaseChatModel`` and ``BaseTool``,
so they are not re-declared here. This module defines the remaining ports that
benefit from an explicit contract: the QA :class:`Reviewer`, which the graph
depends on, the :class:`DocumentStore`, which resolves where tenant documents
live (ADR-0014), the :class:`TenantDirectory`, which maps an identity provider's
organization onto the platform tenant that owns those documents, the
:class:`DeliverableStore`, which keeps every immutable version of a deliverable
and the feedback that prompted it (ADR-0015), the :class:`RunStore`, which holds
run state durably so the one-active-run-per-campaign guard survives a restart and
spans workers, and the :class:`TokenVerifier`, which establishes who a caller is
(ADR-0013), and the :class:`QuestionnaireStore` and :class:`AnswerStore`, which
hold the admin-curated question set and each business's answers to it
(ADR-0018). Tests substitute all of them with hermetic fakes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from marketing_os.schemas import (
    BrandDnaRecord,
    DeliverableVersion,
    DnaAnswer,
    Questionnaire,
    ReviewVerdict,
    RunRecord,
    Tenant,
    VerifiedClaims,
)


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
class DeliverableStore(Protocol):
    """Tenant-scoped, append-only history of every version of every deliverable.

    Separate from the :class:`DocumentStore` because the two answer different
    questions. The document store holds *the* deliverable — one path, one
    content, which is what a specialist reads when it needs its upstream input.
    This store holds *how that deliverable came to be*: each revision appends a
    version recording the feedback that prompted it and whether that feedback
    came from a person or the QA reviewer, and nothing is ever overwritten
    (ADR-0015). The version chain is what makes "compare the versions" and "see
    why this changed" answerable months later.
    """

    def append(
        self,
        tenant: str,
        slug: str,
        stage_key: str,
        content: str,
        *,
        feedback: str | None = None,
        feedback_source: str | None = None,
    ) -> DeliverableVersion:
        """Append a new version of a stage's deliverable.

        The version number is assigned by the store rather than by the caller,
        so two writers cannot both believe they wrote version 3.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable this is.
            content: The full deliverable markdown.
            feedback: The feedback that prompted this version, or ``None`` for
                the first version.
            feedback_source: ``human`` or ``reviewer``, or ``None`` for the first.

        Returns:
            The stored version, carrying the number it was assigned.
        """
        ...

    def latest(self, tenant: str, slug: str, stage_key: str) -> DeliverableVersion | None:
        """Return the newest version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable to read.

        Returns:
            The newest version, or ``None`` when the stage has produced none.
        """
        ...

    def version(
        self, tenant: str, slug: str, stage_key: str, version: int
    ) -> DeliverableVersion | None:
        """Return one historical version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable to read.
            version: The version number to read.

        Returns:
            That version, or ``None`` when it was never written.
        """
        ...

    def history(self, tenant: str, slug: str, stage_key: str) -> list[DeliverableVersion]:
        """Return every version of a stage's deliverable, newest first.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose history to read.

        Returns:
            The versions newest first, empty when the stage has produced none.
        """
        ...

    def stages(self, tenant: str, slug: str) -> list[str]:
        """Return the stage keys a campaign has produced a deliverable for.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The stage keys in mandatory pipeline order.
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
    """Durable record of run state and the one-active-run-per-campaign claim.

    Claiming is the load-bearing operation, because the guard's whole purpose is
    stopping two runs from writing the same campaign's deliverables. Every read
    is tenant-scoped for the same reason the :class:`DocumentStore`'s is — a run
    id belonging to another business must be unfindable, not merely refused
    (ADR-0013).
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

    def set_live_status(self, run_id: str, status: str) -> RunRecord | None:
        """Move a live run between the non-terminal statuses, keeping its claim.

        Used when a run halts at an Approval Gate and when the person's decision
        resumes it. The campaign claim is deliberately **not** released: the
        halted run is the one that will be resumed, and a second run started
        meanwhile would race it over the same deliverables (ADR-0015).

        Args:
            run_id: The run to move.
            status: The non-terminal status to record — ``awaiting_approval``
                while a person decides, or ``running`` once they have. Any other
                value is refused: writing a status the claim index does not
                cover would silently free the campaign.

        Returns:
            The updated record, or ``None`` when the run is already resolved and
            so has no claim left to hold.

        Raises:
            ValidationError: If ``status`` is not one of the live statuses.
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

    def for_campaign(self, tenant: str, slug: str) -> list[RunRecord]:
        """Return every run recorded for a campaign, newest first.

        Listing from the store rather than from disk is what makes a campaign's
        run history complete when several workers are running: each worker only
        has the trace files it wrote itself.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The campaign's runs whatever their status.
        """
        ...

    def reclaim_running(self, status: str) -> list[RunRecord]:
        """Resolve every run still marked running, and return them.

        Called on startup. The service runs as a single process, so a run left
        ``running`` in the store can only be one its predecessor died holding —
        nothing else could be executing it. That assumption is what lets this be
        an unconditional sweep instead of a heartbeat protocol, and it is why
        running two copies of the service would be wrong rather than merely
        unsupported: the second would resolve the first's live runs on boot.

        Args:
            status: The terminal status to record for the abandoned runs.

        Returns:
            The records that were resolved.
        """
        ...


@runtime_checkable
class QuestionnaireStore(Protocol):
    """Holds the published versions of the admin-curated question set.

    The question set is platform-wide, not tenant-scoped: every business answers
    the same curated questions. It is versioned and editable without a deploy,
    because the admin sharpens onboarding as they learn from real businesses
    (ADR-0018).
    """

    def published(self) -> Questionnaire:
        """Return the currently published question set.

        Returns:
            The highest published version, or the code-shipped seed when nothing
            has been published — a fresh deployment still has a usable onboarding.
        """
        ...

    def version(self, version: int) -> Questionnaire | None:
        """Return one published version by number.

        Needed to answer "which questions is this business seeing for the first
        time?" honestly: a question is new only when the version they answered
        did not ask it.

        Args:
            version: The published version number.

        Returns:
            That version, or ``None`` when it was never published.
        """
        ...

    def publish(self, questionnaire: Questionnaire) -> Questionnaire:
        """Publish a new version of the question set.

        Args:
            questionnaire: The version to publish.

        Returns:
            The published version.

        Raises:
            ValidationError: If the version does not advance past the current
                one. Republishing an older version would silently loosen the DNA
                Gate for every business at once.
        """
        ...


@runtime_checkable
class AnswerStore(Protocol):
    """Tenant-scoped storage for a business's Brand DNA answers.

    The structured answers are the source of truth; the markdown the agents read
    is rendered from them (ADR-0018). Scoping is by construction, exactly as the
    :class:`DocumentStore`'s is: a read that does not name the owning tenant
    finds nothing.
    """

    def read(self, tenant: str) -> BrandDnaRecord:
        """Return a business's answers and the question-set version they were given against.

        Args:
            tenant: The tenant whose answers to read.

        Returns:
            The record, empty at version 0 when the business has answered
            nothing — an unstarted onboarding is not an error.
        """
        ...

    def upsert(self, tenant: str, *, version: int, answers: list[DnaAnswer]) -> BrandDnaRecord:
        """Save answers, replacing any previous answer to the same question.

        Upsert rather than replace is what lets onboarding be saved partway and
        resumed, and any single answer be edited later, without the caller
        resending everything it already stored.

        Args:
            tenant: The tenant the answers belong to.
            version: The published question-set version the answers were given
                against, recorded so a later version can be surfaced as a prompt.
            answers: The answers to save.

        Returns:
            The business's full record after the save.
        """
        ...
