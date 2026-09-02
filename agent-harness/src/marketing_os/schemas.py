"""Domain schemas — the framework-free data model of the pipeline.

These Pydantic models are the vocabulary the graph, the reviewer, and the
entrypoints share. They carry no LangChain or LangGraph dependency so the domain
core stays testable in isolation. ``ReviewVerdict`` doubles as the structured
output the QA reviewer is asked to return.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VerifiedClaims(BaseModel):
    """What a signature-checked token asserts, before any tenant resolution.

    This is the raw IdP view of the caller: it names the person and the IdP's
    own organization, and knows nothing about we-OS's tenants. Turning
    ``organization_id`` into the platform tenant is the
    :class:`~marketing_os.ports.TenantDirectory`'s job, which keeps the vendor's
    identifier out of every downstream partition key (ADR-0014).

    Attributes:
        user_id: The IdP's stable subject identifier for the signed-in person.
        organization_id: The IdP's identifier for the business the caller acts
            for — for Clerk, the Organization id (``org_...``).
        email: The signed-in person's email address, when the token carries one.
        business_name: The organization's display name, when the token carries one.
    """

    user_id: str
    organization_id: str
    email: str | None = None
    business_name: str | None = None


class Tenant(BaseModel):
    """One business we-OS markets, as the platform records it.

    The platform mints ``tenant_id`` itself and stores the IdP's
    ``external_auth_id`` beside it, so the identity provider can be swapped, an
    organization re-linked, or a business renamed without rewriting the id that
    every document, run and checkpoint is partitioned by.

    Attributes:
        tenant_id: The platform-owned identifier, and the partition key for
            every document, run and checkpoint the business owns.
        name: The business's display name.
        external_auth_id: The IdP's identifier for the business — for Clerk, the
            Organization id (``org_...``).
    """

    tenant_id: str
    name: str
    external_auth_id: str


class VerifiedIdentity(BaseModel):
    """Who the caller is, and which business they act for.

    Only ever constructed from a signature-checked token resolved through the
    tenant directory — never from a caller-supplied value (ADR-0013). The tenant
    is the unit of ownership: one tenant is exactly one business, so
    ``tenant_id`` scopes every document the request may touch.

    Attributes:
        user_id: The IdP's stable subject identifier for the signed-in person.
        tenant_id: The platform tenant the caller acts for, resolved from the
            verified organization claim.
        organization_id: The IdP organization id the tenant was resolved from,
            kept for support and audit.
        email: The signed-in person's email address, when the token carries one.
        business_name: The tenant's display name.
    """

    user_id: str
    tenant_id: str
    organization_id: str
    email: str | None = None
    business_name: str | None = None


class Discrepancy(BaseModel):
    """One issue the QA reviewer found between a deliverable and its rubric.

    Attributes:
        rubric_point: The rubric item that was violated.
        problem: A specific description of what is wrong.
        fix: The concrete change required to resolve it.
    """

    rubric_point: str
    problem: str
    fix: str


class ReviewVerdict(BaseModel):
    """The QA reviewer's structured judgement of a deliverable.

    Attributes:
        passed: Whether the deliverable satisfies every applicable rubric point.
        summary: A one-sentence overall judgement.
        discrepancies: The issues to resolve; empty when ``passed`` is ``True``.
    """

    passed: bool
    summary: str = ""
    discrepancies: list[Discrepancy] = Field(default_factory=list)

    def as_revision_instruction(self) -> str:
        """Render the discrepancies as a revision brief for the specialist.

        Returns:
            A human-readable instruction that lists every discrepancy and its fix,
            suitable for injecting back into the specialist conversation.
        """
        lines = [
            "Your deliverable did not fully satisfy the professional review rubric. "
            "Revise it to resolve every item below. Keep everything that already "
            "passes; change only what is needed.",
            "",
        ]
        for index, discrepancy in enumerate(self.discrepancies, 1):
            lines.append(f"{index}. [{discrepancy.rubric_point}] {discrepancy.problem}")
            if discrepancy.fix:
                lines.append(f"   Fix: {discrepancy.fix}")
        return "\n".join(lines)


class Usage(BaseModel):
    """Provider-normalized token accounting for one or more model calls.

    Attributes:
        input_tokens: Prompt tokens consumed.
        output_tokens: Completion tokens produced.
        cache_read_input_tokens: Prompt tokens served from the provider cache.
        cache_creation_input_tokens: Prompt tokens written to the provider cache.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Return the sum of input and output tokens."""
        return self.input_tokens + self.output_tokens


class StageResult(BaseModel):
    """The outcome of running one pipeline stage end-to-end.

    Attributes:
        stage: The stage key.
        deliverable_path: The repo-relative path of the written deliverable.
        qa_iterations: How many QA revision rounds the stage took.
        save_retries: How many save-retry prompts the stage required.
        verdict: The final QA verdict, if the stage was reviewed.
        approved: Whether the stage was approved to advance.
    """

    stage: str
    deliverable_path: str
    qa_iterations: int = 0
    save_retries: int = 0
    verdict: ReviewVerdict | None = None
    approved: bool = True


class CampaignResult(BaseModel):
    """The outcome of running a campaign through the pipeline.

    Attributes:
        tenant: The tenant name the campaign was run for.
        slug: The campaign slug.
        stages: The per-stage results in pipeline order.
        usage: The aggregated token usage across every model call.
        run_log: The repo-relative path of the run's JSONL trace, if written.
    """

    tenant: str
    slug: str
    stages: list[StageResult] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    run_log: str | None = None


class RunRecord(BaseModel):
    """One execution attempt of a campaign's pipeline, as the run store records it.

    The record is what makes the one-active-run-per-campaign guard real: the
    store claims ``(tenant_id, slug)`` durably, so a second request is refused
    rather than racing on the same deliverables. The claim also names the person
    who took it, because a campaign is driven by one person at a time — a
    colleague in the same business is refused as firmly as a second tab is.

    Attributes:
        run_id: The unique id of this execution attempt, and its trace filename.
        tenant_id: The tenant the run belongs to.
        user_id: The person who started the run, and the only one who may
            cancel it while it is in flight.
        slug: The campaign slug the run claims.
        stage: The single stage being run, or ``None`` for the full pipeline.
        status: One of ``running``, ``completed``, ``failed``, ``cancelled``, or
            ``interrupted``.
        started_at: When the run was claimed, as a UTC epoch timestamp.
    """

    run_id: str
    tenant_id: str
    slug: str
    user_id: str = ""
    stage: str | None = None
    status: str = "running"
    started_at: float = 0.0
