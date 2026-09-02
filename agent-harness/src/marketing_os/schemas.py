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


class Question(BaseModel):
    """One admin-curated question the business owner answers about their business.

    A question asks only for a fact the owner uniquely knows. Crafted artifacts —
    positioning, value proposition, messaging, brand voice, channel selection —
    are produced by the engine and approved at the stage gates, never asked for
    here (ADR-0018).

    Attributes:
        id: The stable question id answers reference; it survives rewording.
        field: The Brand DNA field this question populates, which is also the
            label the DNA Gate checks and the renderer writes.
        section: The Brand DNA section the field is rendered under.
        text: The question as the owner reads it.
        why_we_ask: Why the question is asked, so every question explains itself.
        help_text: What a good answer looks like.
        input_type: How the wizard renders the input.
        required: Whether an answer is Required — Required answers feed the DNA
            Gate, recommended ones only sharpen the work.
        options: The choices for ``select`` and ``multi_select`` inputs.
    """

    id: str
    field: str
    section: str
    text: str
    why_we_ask: str
    help_text: str
    input_type: str = "text"
    required: bool = True
    options: list[str] = Field(default_factory=list)


class Questionnaire(BaseModel):
    """One published version of the admin-curated question set.

    The single artifact driving the onboarding wizard, the shape of the rendered
    Brand DNA, and what the DNA Gate enforces as Required — so the three cannot
    drift apart (ADR-0018).

    Attributes:
        version: The published version number, which answers record so a tenant
            answering an older set is prompted rather than silently blocked.
        published_at: When the version was published, as an ISO-8601 timestamp.
        questions: The questions in the order the wizard asks them.
    """

    version: int
    published_at: str
    questions: list[Question] = Field(default_factory=list)

    @property
    def required_questions(self) -> list[Question]:
        """Return the Required questions, whose fields the DNA Gate enforces."""
        return [question for question in self.questions if question.required]

    def question(self, question_id: str) -> Question | None:
        """Return one question by id.

        Args:
            question_id: The stable question id.

        Returns:
            The question, or ``None`` when this version has no such question.
        """
        return next((q for q in self.questions if q.id == question_id), None)


class DnaAnswer(BaseModel):
    """One business owner's answer to one questionnaire question.

    Attributes:
        question_id: The question this answers.
        answer: The answer text, exactly as the owner wrote it.
    """

    question_id: str
    answer: str


class BrandDnaRecord(BaseModel):
    """A tenant's structured Brand DNA answers and the version they were given against.

    The structured answers are the source of truth; the markdown agents read is
    a derived projection rendered from them (ADR-0018).

    Attributes:
        questionnaire_version: The question-set version the answers were given
            against, which is what makes "your DNA predates a newer version"
            answerable rather than a silent gate failure.
        updated_at: When an answer was last saved, as an ISO-8601 timestamp, or
            ``None`` when the business has answered nothing yet.
        answers: The answers, one per answered question.
    """

    questionnaire_version: int
    updated_at: str | None = None
    answers: list[DnaAnswer] = Field(default_factory=list)

    def answer_for(self, question_id: str) -> str | None:
        """Return the answer text for a question.

        Args:
            question_id: The stable question id.

        Returns:
            The answer text, or ``None`` when the question is unanswered.
        """
        return next((a.answer for a in self.answers if a.question_id == question_id), None)


class MissingField(BaseModel):
    """One Required Brand DNA field the business has not yet supplied.

    Attributes:
        question_id: The question that would supply the field.
        field: The Brand DNA field's label.
        label: The question text, so the report reads as a prompt to answer
            rather than as an internal field name.
    """

    question_id: str
    field: str
    label: str


class DnaCompleteness(BaseModel):
    """What stands between a business and starting work.

    Attributes:
        complete: Whether every Required field is answered.
        questionnaire_version: The published version the report was computed against.
        required_total: How many Required fields the published version has.
        required_answered: How many of them this business has answered.
        missing: Every unanswered Required field, named exactly.
        unanswered_new_questions: Question ids a newer published version added
            that this business's answers predate — surfaced as a prompt.
    """

    complete: bool
    questionnaire_version: int
    required_total: int
    required_answered: int
    missing: list[MissingField] = Field(default_factory=list)
    unanswered_new_questions: list[str] = Field(default_factory=list)
