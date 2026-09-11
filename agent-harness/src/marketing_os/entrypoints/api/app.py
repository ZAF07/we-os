"""FastAPI service exposing the Marketing OS graph over HTTP.

Endpoints:
  GET  /health                          -> liveness; the only unauthenticated route
  GET  /me                              -> the verified identity and its tenant
  PUT  /tenant/tier                     -> record the business's tier, once
  GET  /usage                           -> spend against credits, per tenant and campaign
  GET  /questionnaire                   -> the published question set
  GET  /brand-dna                       -> the tenant's answers and rendered markdown
  GET  /brand-dna/completeness          -> what still stands between them and a run
  POST /brand-dna/answers               -> save answers, returning the updated report
  DELETE /brand-dna/answers/{id}        -> withdraw one answer, returning the updated report
  GET  /brand-dna/segments              -> the audience segments a campaign may target
  POST /campaigns                       -> create a campaign from its goal (201)
  GET  /campaigns                       -> list active campaigns with status and progress
  GET  /campaigns/{slug}                -> one campaign: goal, status, per-stage state
  POST /campaigns/{slug}/archive        -> archive a campaign; it leaves the active list
  GET  /campaigns/{slug}/gate           -> Stage 0 gate report
  GET  /campaigns/{slug}/deliverables   -> list written deliverables
  GET  /campaigns/{slug}/stages         -> stages with approval policy, version and staleness
  POST /campaigns/{slug}/stages/{key}/reopen -> revise an approved stage; downstream goes stale
  GET  /campaigns/{slug}/deliverables/{name}/versions -> a deliverable's version history
  GET  /campaigns/{slug}/deliverables/{name}/versions/{v} -> one historical version
  POST /campaigns/{slug}/run            -> start a background run, return its run_id (202)
  GET  /runs                            -> list in-flight runs
  GET  /runs/{run_id}                   -> report a run's lifecycle status
  POST /runs/{run_id}/cancel            -> cancel an in-flight run
  POST /runs/{run_id}/approve           -> approve the stage at the gate; the run resumes
  POST /runs/{run_id}/revise            -> send the stage back with feedback (new version)
  GET  /runs/{run_id}/clarifications    -> the questions a halted run is asking the business
  POST /runs/{run_id}/clarifications    -> answer them; they join the Brand DNA and the run resumes
  GET  /runs/{run_id}/stream            -> attach to a run and tail its trace as SSE

Every route except ``/health`` requires a verified bearer token, and the tenant
is derived from that token's claim — no operation accepts a business identity as
a parameter (ADR-0013). Resources belonging to another tenant answer 404 rather
than 403, so a foreign id is indistinguishable from a missing one.

Run with:  uvicorn marketing_os.entrypoints.api.app:app --reload
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from pydantic import BaseModel, field_validator
from pydantic import Field as PydanticField

from marketing_os.adapters.auth import JwksTokenVerifier, RefusalClass, log_refusal
from marketing_os.adapters.observability import (
    configure_logging,
    configure_tracing,
    get_logger,
    list_run_ids,
    new_run_id,
    read_events,
    tail_trace,
)
from marketing_os.adapters.questionnaire import now_iso
from marketing_os.adapters.runs import (
    AWAITING_APPROVAL,
    AWAITING_CLARIFICATION,
    CANCELLED,
    HELD_STATUSES,
    RUNNING,
)
from marketing_os.adapters.usage import whole_credits
from marketing_os.campaign import (
    Budget,
    CampaignGoal,
    KpiTiers,
    Timeframe,
    allocate_slug,
    audience_segments,
    missing_goal_fields,
    parse_campaign_goal,
    render_campaign_goal,
)
from marketing_os.campaign.progress import (
    StageProgress,
    produced_deliverables,
    progress_from_latest,
    stale_keys,
)
from marketing_os.config import Settings, load_settings
from marketing_os.entrypoints.env import load_env
from marketing_os.errors import (
    ConfigError,
    DocumentNotFoundError,
    GateError,
    MarketingOSError,
    QuotaExhaustedError,
    RevisionLimitError,
    RunConflictError,
    RunLimitError,
    RunNotAwaitingClarificationError,
    StageNotAwaitingApprovalError,
    UnauthenticatedError,
    ValidationError,
)
from marketing_os.governance import check_gate
from marketing_os.governance.pipeline import (
    PIPELINE,
    PIPELINE_BY_KEY,
)
from marketing_os.graph.registry import RunRegistry, read_run_status, resolve_trace_path
from marketing_os.graph.runner import arun_campaign, awaiting_approval_stage, pending_hold
from marketing_os.ports import (
    AnswerStore,
    DeliverableStore,
    DocumentStore,
    QuestionnaireStore,
    RunStore,
    StorageBackend,
    TenantDirectory,
    TokenVerifier,
    UsageLedger,
)
from marketing_os.questionnaire import completeness, render_brand_dna
from marketing_os.schemas import (
    CLARIFICATION_HOLD,
    TIER_NAMES,
    ApprovalDecision,
    BrandDnaRecord,
    CampaignResult,
    Clarification,
    Consumption,
    DeliverableVersion,
    DnaAnswer,
    DnaCompleteness,
    Questionnaire,
    RunHold,
    RunRecord,
    VerifiedIdentity,
    human_revisions_used,
    tier_from_name,
)

if TYPE_CHECKING:
    pass

_LOGGER = get_logger("marketing_os.api")

load_env()


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Open the service's stores, resolve runs a crash left behind, then serve.

    Reclaiming on startup turns a crash or a deploy from "runs vanish and stay
    ``running`` forever" into "runs are resolved as ``interrupted`` and their
    campaigns start clean". It is an unconditional sweep, which is only correct
    because the service is a single process (ADR-0025).

    Args:
        _: The FastAPI application (unused).

    Yields:
        Control for the duration of the application's lifespan.
    """
    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)

    backend = get_backend()
    await backend.open()

    registry = get_registry()
    _LOGGER.info("service.started")
    reclaimed = await registry.reclaim_abandoned()
    if reclaimed:
        _LOGGER.info("service.reclaimed runs=%d", len(reclaimed))
    try:
        yield
    finally:
        await backend.close()
        reset_providers()


app = FastAPI(title="Marketing OS", version="0.2.0", lifespan=_lifespan)


@app.exception_handler(HTTPException)
async def _error_body(_: Request, exc: HTTPException) -> JSONResponse:
    """Render errors as the contract's top-level ``Error`` object.

    FastAPI nests ``HTTPException.detail`` under a ``detail`` key, but the frozen
    contract defines ``Error`` as the response body itself. This unwraps the
    structured payload so the frontend codes against the contract rather than
    against the framework's envelope.

    Args:
        _: The inbound request (unused).
        exc: The exception raised by an endpoint or dependency.

    Returns:
        The JSON error response, with ``type``, ``status`` and ``message`` at the
        top level.
    """
    if isinstance(exc.detail, dict):
        body: dict[str, object] = dict(exc.detail)
    else:
        body = {"message": str(exc.detail)}
    body.setdefault("type", "internal")
    body.setdefault("status", exc.status_code)
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


def _http_error(exc: MarketingOSError) -> HTTPException:
    """Map a harness error to an HTTP error using the error's own presentation.

    The status code, the contract's ``type`` discriminator and the structured
    payload all come from the exception itself, so the taxonomy is not re-spelled
    at each endpoint.

    Args:
        exc: The harness error to translate.

    Returns:
        The HTTP exception carrying the error's status and detail payload.
    """
    detail = exc.detail or {
        "type": exc.error_type,
        "status": exc.http_status,
        "message": str(exc),
    }
    return HTTPException(exc.http_status, detail)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached harness settings.

    Returns:
        The process-wide :class:`Settings` instance.
    """
    return load_settings()


_backend_override: StorageBackend | None = None
"""A backend a test installed through :func:`use_backend`, or ``None``.

``None`` in every deployment. Storage is one durability decision (ADR-0014), so
this is a single seam rather than eight: a test swaps the whole backend, and no
getter below can be seeded independently into a state no deployment has.
"""


@lru_cache(maxsize=1)
def get_backend() -> StorageBackend:
    """Return the Postgres backend every store resolves through.

    The single place the storage choice is made, and therefore the single place
    it is enforced. Postgres is the only production backend: a deploy with no
    DSN fails here rather than booting healthy on local disk with a checkpointer
    that does not survive a restart. The prototype filesystem and in-memory
    adapters still exist for tests, but nothing selects them implicitly.

    Returns:
        The backend. The lifespan opens and closes it, whichever it is.

    Raises:
        ConfigError: If no connection string is configured.
    """
    if _backend_override is not None:
        return _backend_override
    dsn = get_settings().postgres_dsn
    if not dsn:
        raise ConfigError(
            "No database configured. Set MARKETING_OS_POSTGRES_DSN (or DATABASE_URL) "
            "to the Postgres the service stores campaigns, runs and checkpoints in."
        )
    from marketing_os.adapters.postgres import PostgresBackend

    return PostgresBackend(dsn)


@lru_cache(maxsize=1)
def get_document_store() -> DocumentStore:
    """Return the process-wide document store tenant documents resolve through.

    Returns:
        The configured backend's document store.
    """
    return get_backend().documents


@lru_cache(maxsize=1)
def get_deliverable_store() -> DeliverableStore:
    """Return the process-wide store holding each deliverable's version history.

    Returns:
        The Postgres adapter, where a halted run's history survives a restart.
    """
    return get_backend().deliverables


@lru_cache(maxsize=1)
def get_tenant_directory() -> TenantDirectory:
    """Return the process-wide directory mapping IdP organizations to tenants.

    Returns:
        The Postgres directory, which mints a platform ``tenant_id`` and keeps
        the IdP's organization id in its own column (ADR-0014).
    """
    return get_backend().tenants


@lru_cache(maxsize=1)
def get_checkpointer() -> BaseCheckpointSaver:
    """Return the process-wide checkpointer runs are resumable through.

    A single instance for the process — not one per run — is what makes a
    checkpoint outlive the run that wrote it, and therefore what makes
    abandoning a cancelled run's threads a real operation rather than a no-op.

    Returns:
        The Postgres saver, whose checkpoints survive a restart — which is what
        makes a run halted at an Approval Gate resumable at all.
    """
    return get_backend().checkpointer


@lru_cache(maxsize=1)
def get_run_store() -> RunStore:
    """Return the process-wide store holding run claims and statuses.

    Returns:
        The Postgres store, shared by every worker.
    """
    return get_backend().runs


@lru_cache(maxsize=1)
def get_questionnaire_store() -> QuestionnaireStore:
    """Return the process-wide store holding the published question set.

    Returns:
        The Postgres store, where an admin publishes a new version without a
        deploy.
    """
    return get_backend().questionnaires


@lru_cache(maxsize=1)
def get_answer_store() -> AnswerStore:
    """Return the process-wide store holding each business's Brand DNA answers.

    Returns:
        The Postgres store holding each business's answers.
    """
    return get_backend().answers


@lru_cache(maxsize=1)
def get_usage_ledger() -> UsageLedger:
    """Return the process-wide Usage Ledger every billable call is charged to.

    Returns:
        The Postgres ledger, where what a tenant spent survives a restart —
        which is the whole point of enforcing a quota.
    """
    return get_backend().usage


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifier:
    """Return the process-wide verifier for inbound bearer tokens.

    Returns:
        A :class:`JwksTokenVerifier` bound to the configured OIDC issuer.

    Raises:
        ConfigError: If no issuer is configured. The service refuses every
            authenticated request rather than falling open, so a missing
            configuration can never silently disable tenancy.
    """
    settings = get_settings()
    if not settings.auth_issuer:
        raise ConfigError(
            "No auth issuer configured. Set MARKETING_OS_AUTH_ISSUER (or "
            "CLERK_ISSUER_URL) to the IdP that issues your tokens."
        )
    return JwksTokenVerifier(issuer=settings.auth_issuer, audience=settings.auth_audience)


def get_identity(request: Request) -> VerifiedIdentity:
    """Resolve the caller's verified identity from the ``Authorization`` header.

    Two steps, deliberately separate. The token verifier says who the caller is
    and which **IdP organization** they act for; the tenant directory says which
    **platform tenant** owns that organization's data, registering it on a
    business's first request. Keeping them apart is what stops a vendor's
    identifier — Clerk's ``org_...`` — from becoming the partition key for every
    document, run and checkpoint (ADR-0014).

    This is the only place a tenant enters the service. Tests override it via
    ``app.dependency_overrides[get_identity]`` to inject a claim, so no test
    contacts a live IdP.

    The header is checked before either provider is built, so a request with no
    token answers 401 even when the service is misconfigured — an unauthenticated
    caller learns "sign in", not "the server is broken". Every refusal is logged
    server-side with its failure class, since the uniform 401 the caller sees is
    for the probe's benefit, not the operator's.

    Args:
        request: The inbound request carrying the bearer token.

    Returns:
        The verified identity, whose ``tenant_id`` scopes the whole request.

    Raises:
        HTTPException: 401 if the header is absent, malformed, or the token
            does not verify.
    """
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        log_refusal(RefusalClass.MISSING_HEADER, request.url.path)
        raise _http_error(UnauthenticatedError("Sign in to continue."))
    try:
        claims = get_token_verifier().verify(token.strip(), request_path=request.url.path)
        tenant = get_tenant_directory().resolve(
            external_auth_id=claims.organization_id, name=claims.business_name
        )
    except MarketingOSError as exc:
        raise _http_error(exc) from exc
    return VerifiedIdentity(
        user_id=claims.user_id,
        tenant_id=tenant.tenant_id,
        organization_id=tenant.external_auth_id,
        email=claims.email,
        business_name=tenant.name,
        tier=tenant.tier,
    )


Identity = Annotated[VerifiedIdentity, Depends(get_identity)]


@lru_cache(maxsize=1)
def get_registry() -> RunRegistry:
    """Return this worker's registry of background runs.

    One instance per process (tests reset it with ``get_registry.cache_clear()``,
    mirroring :func:`get_settings`). The claims and statuses it reads and writes
    live in the run store, so both survive a restart.

    Returns:
        The process's :class:`RunRegistry`.
    """
    return RunRegistry(get_run_store(), checkpointer=get_checkpointer())


_BACKED_PROVIDERS = (
    get_backend,
    get_document_store,
    get_deliverable_store,
    get_tenant_directory,
    get_checkpointer,
    get_run_store,
    get_questionnaire_store,
    get_answer_store,
    get_usage_ledger,
    get_registry,
)


def reset_providers() -> None:
    """Drop every cached provider so the next call rebuilds it.

    Called when the service shuts down, and by tests between cases, since every
    provider's answer depends on the settings and the storage backend.
    """
    for provider in _BACKED_PROVIDERS:
        provider.cache_clear()


def use_backend(backend: StorageBackend | None) -> None:
    """Install a storage backend in place of the one the DSN would select.

    The single seam for tests. Postgres is the only backend production selects,
    so :func:`get_backend` raises without a DSN rather than falling back to local
    disk; a test wanting the prototype filesystem and in-memory adapters hands
    one in here, out loud. Swapping the whole backend rather than seeding the
    getters one by one is what keeps storage a single durability decision
    (ADR-0014) — no test can produce a half-Postgres state that no deployment has.

    Nothing in the service calls this: it is import-visible so the test suite can
    reach it, and passing ``None`` restores the configured backend.

    Args:
        backend: The backend every store resolves through, or ``None`` to go
            back to the one the DSN selects.
    """
    global _backend_override
    _backend_override = backend
    reset_providers()


class SetTier(BaseModel):
    """Request body for recording the business's tier.

    Carries the tier alone: the business it belongs to comes from the verified
    token, never from the body (ADR-0013).

    Attributes:
        tier: The name of the tier chosen, as the tier card sent it.
    """

    tier: str


class DnaAnswersUpsert(BaseModel):
    """Request body for saving Brand DNA answers.

    Upsert rather than replace, so the wizard can save partway and resume, and a
    single answer can be edited later without resending the rest.

    Attributes:
        answers: The answers to save; at least one, each carrying content.
    """

    answers: list[DnaAnswer]

    @field_validator("answers")
    @classmethod
    def _require_non_blank(cls, answers: list[DnaAnswer]) -> list[DnaAnswer]:
        """Refuse a save carrying an answer that is empty or only whitespace.

        Withdrawing an answer is its own operation, so a blank is never a way to
        express one — it would leave a row the completeness report counts as
        answered and the projection renders as an empty label. Refusing it on the
        way in covers every save without making an already-stored blank row
        unreadable, which validating :class:`DnaAnswer` itself would.

        Args:
            answers: The answers as submitted.

        Returns:
            The answers unchanged.

        Raises:
            ValueError: If any answer holds no non-whitespace character.
        """
        blank = [answer.question_id for answer in answers if not answer.answer.strip()]
        if blank:
            raise ValueError(
                f"An answer cannot be blank; delete it instead: {', '.join(sorted(blank))}."
            )
        return answers


class CreateCampaign(BaseModel):
    """Request body for creating a campaign from its goal.

    Carries no business identity: the tenant comes from the verified token
    (ADR-0013), so this body describes only the campaign itself. It carries no
    channels either — those are the performance specialist's decision at stage 4
    (ADR-0016), not something the business owner is asked for.

    Every field is optional here so an incomplete body is refused by naming the
    fields it is missing, rather than by Pydantic's generic schema error.

    Attributes:
        name: The campaign's display name.
        objective: One measurable business objective.
        timeframe: When the campaign runs.
        budget: The media spend available to it.
        audience_segment: The Brand DNA segment this campaign targets.
        kpis: All three KPI tiers.
        offer: The promotion being run, if any.
        constraints: Anything unique to this campaign beyond the DNA constraints.
    """

    name: str = ""
    objective: str = ""
    timeframe: Timeframe = PydanticField(default_factory=Timeframe)
    budget: Budget = PydanticField(default_factory=Budget)
    audience_segment: str = ""
    kpis: KpiTiers = PydanticField(default_factory=KpiTiers)
    offer: str = ""
    constraints: str = ""


class RunCampaign(BaseModel):
    """Request body for running a campaign.

    Attributes:
        stage: The single stage to run, or ``None`` for the full pipeline.
    """

    stage: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Report service health and the active provider and root.

    Liveness only — it carries no tenant data and needs no identity, so it is
    the one route exempt from authentication.

    Returns:
        A status payload.
    """
    settings = get_settings()
    return {"status": "ok", "provider": settings.provider, "root": str(settings.root)}


@app.get("/me")
def me(identity: Identity) -> dict[str, object]:
    """Report the signed-in user and the business their tenant represents.

    Args:
        identity: The verified identity, resolved from the bearer token.

    Returns:
        The user id, email, and business name from the verified claim, and the
        tier the business has recorded — ``None`` until it has one, which is
        how the interface knows to send a new business back to finish.
    """
    return {
        "user_id": identity.user_id,
        "email": identity.email,
        "business_name": identity.business_name or identity.tenant_id,
        "tier": identity.tier,
    }


@app.put("/tenant/tier")
def set_tenant_tier(body: SetTier, identity: Identity) -> dict[str, object]:
    """Record the business's tier, once (ADR-0027).

    The first call a new business makes: resolving the identity has just minted
    its tenant, and this attaches the tier the person chose before they had an
    account. Repeating the recorded tier succeeds and changes nothing, so the
    welcome flow can retry after a transient failure without creating anything
    twice. Naming a different tier is refused with the typed 409 — a tier change
    is a billing event, and billing does not exist yet.

    Args:
        body: The tier to record.
        identity: The verified identity whose tenant the tier is recorded on.

    Returns:
        The tier the business now has recorded.

    Raises:
        HTTPException: 422 for a name that is not one of the three tiers, 409
            when a different tier is already recorded.
    """
    tier = tier_from_name(body.tier)
    if tier is None:
        raise _http_error(
            ValidationError(f"Unknown tier '{body.tier}'. Choose one of: {', '.join(TIER_NAMES)}.")
        )
    try:
        tenant = get_tenant_directory().set_tier(identity.tenant_id, tier)
    except MarketingOSError as exc:
        raise _http_error(exc) from exc
    return {"tier": tenant.tier}


@app.get("/usage")
def usage(identity: Identity, slug: str | None = None) -> dict[str, object]:
    """Report the tenant's spend against their credits, and where it went.

    The read behind "how much of my credits have I used?" — so a business
    owner is not surprised by work stopping — and behind the platform's
    unit-economics question, since the per-campaign breakdown is the same rows
    totalled more finely (ADR-0020).

    Cost accounting is deliberately distinct from the **campaign budget**, which
    is the business's own media spend allocated by the Performance Plan. This
    endpoint reports what the platform spent on models, never what the business
    spends on ads.

    Args:
        identity: The verified identity whose tenant's spend is reported.
        slug: One campaign to restrict the total to, or omitted for everything
            the tenant has spent.

    Credits are derived from the recorded cost at the platform-wide rate and
    reported as whole numbers, since a fractional credit is display noise. The
    quota check compares the unrounded value, so what is shown never decides
    when work is refused.

    Returns:
        The spend, the credits, what remains, and the per-campaign breakdown,
        all in whole credits. Another tenant's spend is never included.
    """
    report: Consumption = get_usage_ledger().consumption(identity.tenant_id, slug)
    return {
        "used": whole_credits(report.used),
        "credits": whole_credits(report.credits),
        "remaining": whole_credits(report.remaining),
        "exhausted": report.exhausted,
        "campaigns": [
            {"slug": campaign.slug, "used": whole_credits(campaign.used)}
            for campaign in report.campaigns
        ],
    }


DNA_DOCUMENT = "dna.md"


def read_brand_dna(tenant: str) -> tuple[Questionnaire, BrandDnaRecord]:
    """Return the published question set and one business's answers to it.

    Args:
        tenant: The tenant whose answers to read.

    Returns:
        The published questionnaire and the tenant's record.
    """
    return get_questionnaire_store().published(), get_answer_store().read(tenant)


def project_brand_dna(
    identity: VerifiedIdentity, questionnaire: Questionnaire, record: BrandDnaRecord
) -> str:
    """Render a business's answers to markdown and store it as their Brand DNA.

    The structured answers are the source of truth; ``dna.md`` is their canonical
    projection, and it is rewritten on every save so the document the specialists
    read and the document the gate checks can never lag the answers (ADR-0018).

    Args:
        identity: The verified identity whose tenant owns the DNA.
        questionnaire: The published question set defining the fields and their order.
        record: The business's answers.

    Returns:
        The rendered markdown, as written to the document store.
    """
    markdown = render_brand_dna(
        questionnaire,
        record,
        business_name=identity.business_name or identity.tenant_id,
    )
    get_document_store().write(identity.tenant_id, DNA_DOCUMENT, markdown)
    return markdown


def dna_completeness(tenant: str) -> DnaCompleteness:
    """Return the completeness report for a business's Brand DNA.

    Args:
        tenant: The tenant whose DNA to report on.

    Returns:
        The report, naming every missing Required field and every question a
        newer published version added that this business has not been shown.
    """
    published, record = read_brand_dna(tenant)
    answered_against = get_questionnaire_store().version(record.questionnaire_version)
    return completeness(published, record, answered_against=answered_against)


@app.get("/questionnaire")
def questionnaire(identity: Identity) -> Questionnaire:
    """Return the currently published question set.

    The single artifact driving the onboarding wizard, the shape of the rendered
    Brand DNA, and what the DNA Gate enforces as Required — so the wizard renders
    entirely from this rather than hardcoding questions (ADR-0018). The set is
    the same for every business, but reading it still needs a verified caller:
    the questions are the platform's curation, not public material.

    Args:
        identity: The verified identity (unused; the set is platform-wide).

    Returns:
        The published question set.
    """
    return get_questionnaire_store().published()


@app.get("/brand-dna")
def brand_dna(identity: Identity) -> dict[str, object]:
    """Return a business's Brand DNA in both its forms.

    Args:
        identity: The verified identity whose tenant owns the DNA.

    Returns:
        The question-set version answered, when it was last saved, the canonical
        markdown projection, the structured answers behind it, and every
        Clarification a specialist asked for and the business answered — its
        own section, never Required (ADR-0028).
    """
    published, record = read_brand_dna(identity.tenant_id)
    return {
        "questionnaire_version": record.questionnaire_version,
        "updated_at": record.updated_at,
        "markdown": render_brand_dna(
            published,
            record,
            business_name=identity.business_name or identity.tenant_id,
        ),
        "answers": [answer.model_dump() for answer in record.answers],
        "clarifications": [item.model_dump() for item in record.clarifications],
    }


@app.get("/brand-dna/completeness")
def brand_dna_completeness(identity: Identity) -> DnaCompleteness:
    """Report what stands between a business and starting work.

    Args:
        identity: The verified identity whose tenant owns the DNA.

    Returns:
        The completeness report, naming every unanswered Required field and any
        question a newer published version added.
    """
    return dna_completeness(identity.tenant_id)


@app.post("/brand-dna/answers")
def answer_brand_dna(body: DnaAnswersUpsert, identity: Identity) -> DnaCompleteness:
    """Save questionnaire answers and report what remains.

    Every save re-renders the Brand DNA markdown, so the document the gate reads
    is never behind the answers. The report comes back with the save so the
    wizard shows progress without a second request.

    Args:
        body: The answers to save.
        identity: The verified identity whose tenant owns the DNA.

    Returns:
        The updated completeness report.

    Raises:
        HTTPException: 422 if no answers were sent, or one names a question the
            published set does not ask — a silently dropped answer would look
            saved to the business and be absent from their DNA.
    """
    published = get_questionnaire_store().published()
    if not body.answers:
        raise _http_error(ValidationError("Send at least one answer."))
    unknown = [
        answer.question_id
        for answer in body.answers
        if published.question(answer.question_id) is None
    ]
    if unknown:
        raise _http_error(
            ValidationError(
                f"The published questionnaire does not ask: {', '.join(sorted(unknown))}."
            )
        )
    record = get_answer_store().upsert(
        identity.tenant_id, version=published.version, answers=body.answers
    )
    project_brand_dna(identity, published, record)
    answered_against = get_questionnaire_store().version(record.questionnaire_version)
    return completeness(published, record, answered_against=answered_against)


@app.delete("/brand-dna/answers/{question_id}")
def remove_brand_dna_answer(question_id: str, identity: Identity) -> DnaCompleteness:
    """Withdraw one questionnaire answer and report what remains.

    Its own operation rather than saving a blank, because absence from a save
    means "leave it alone" — what makes partial saves resumable — so a removal
    cannot be expressed through it. Like a save, it re-renders the Brand DNA
    markdown so the document the gate reads never keeps a field the answers no
    longer have, and returns the report so the caller can show completeness
    changing without a second request.

    Args:
        question_id: The question to leave unanswered.
        identity: The verified identity whose tenant owns the DNA.

    Returns:
        The updated completeness report.

    Raises:
        HTTPException: 404 if the published set does not ask that question, as
            the save endpoint refuses an answer to one.
    """
    published = get_questionnaire_store().published()
    if published.question(question_id) is None:
        raise _http_error(
            DocumentNotFoundError(f"The published questionnaire does not ask: {question_id}.")
        )
    record = get_answer_store().remove(identity.tenant_id, question_id=question_id)
    project_brand_dna(identity, published, record)
    answered_against = get_questionnaire_store().version(record.questionnaire_version)
    return completeness(published, record, answered_against=answered_against)


ARCHIVED = "archived"
_ARCHIVE_MARKER = "archived.md"
_GOAL_DOCUMENT = "goal.md"


def _campaign_slugs(tenant: str, store: DocumentStore) -> list[str]:
    """List every campaign slug the tenant owns.

    Campaigns are derived from the documents themselves rather than from a
    separate registry, so a goal authored by hand is a campaign on equal terms
    with one created through the interface, and the two can never disagree.

    Args:
        tenant: The tenant whose campaigns are listed.
        store: The tenant-scoped document store.

    Returns:
        The slugs, in sorted order.
    """
    return _slugs_in(store.list(tenant, "campaigns"))


def _slugs_in(paths: list[str]) -> list[str]:
    """Return the campaign slugs a listing of a tenant's documents names.

    A campaign is a directory holding a goal document, so the goal is what makes
    a slug a campaign. Taken as already-listed paths rather than as a store, so
    the same rule serves a caller that has the listing in hand.

    Args:
        paths: Tenant-relative document paths under ``campaigns``.

    Returns:
        The slugs, in sorted order.
    """
    return sorted(
        {
            path.split("/")[1]
            for path in paths
            if path.count("/") >= 2 and path.endswith(f"/{_GOAL_DOCUMENT}")
        }
    )


def _archived_slugs_in(paths: list[str]) -> set[str]:
    """Return the campaign slugs a listing shows an archive marker for.

    The bulk counterpart of :func:`_is_archived`, reading the same marker
    document from a listing the caller already has.

    Args:
        paths: Tenant-relative document paths under ``campaigns``.

    Returns:
        The archived slugs.
    """
    return {
        path.split("/")[1]
        for path in paths
        if path.count("/") >= 2 and path.endswith(f"/{_ARCHIVE_MARKER}")
    }


def _named_goal(document: str, slug: str) -> CampaignGoal:
    """Parse a goal document, falling back to the slug for an unnamed campaign.

    A goal authored by hand may carry no title, so the campaign still needs a
    name to show. The slug is the honest fallback: it is what the business will
    see in the URL.

    Args:
        document: The goal document's markdown.
        slug: The campaign slug, used as the name when the document is untitled.

    Returns:
        The structured goal, always carrying a name.
    """
    goal = parse_campaign_goal(document)
    if not goal.name.strip():
        return goal.model_copy(update={"name": slug})
    return goal


@dataclass(frozen=True)
class _CampaignRecord:
    """One campaign as the stores hold it, before anything is derived from it.

    Attributes:
        slug: The campaign slug.
        goal: The campaign's goal, always carrying a name.
        latest: The newest version of each stage that has produced one, keyed
            by stage key; stages that produced nothing are absent.
        archived: Whether the archive marker has been written beside the goal.
        halted: The live run holding on a person — at an Approval Gate, or for
            an answer — if one is. What it is holding for is a checkpoint read,
            not a store read, so it is resolved by the caller.
    """

    slug: str
    goal: CampaignGoal
    latest: dict[str, DeliverableVersion]
    archived: bool
    halted: RunRecord | None


def _read_campaign(
    tenant: str,
    slug: str,
    store: DocumentStore,
    deliverables: DeliverableStore,
    registry: RunRegistry,
) -> _CampaignRecord | None:
    """Read one campaign from the stores, in three reads whatever it has produced.

    One read of the goal and the archive marker together, one of the newest
    version of every stage, and one of the campaign's live run — the same
    three however many stages have produced work. Every one is a synchronous
    store call, so they are gathered here for the caller to run off the event
    loop together, as the list does with :func:`_read_portfolio`.

    A slug owned by another tenant is simply absent from this tenant's store,
    so it is indistinguishable from one that was never created (ADR-0013).

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.
        store: The tenant-scoped document store.
        deliverables: The store holding each stage's version chain.
        registry: The registry naming which campaigns have a live run.

    Returns:
        The campaign as stored, or ``None`` when the tenant has no such
        campaign.
    """
    goal_document = f"campaigns/{slug}/{_GOAL_DOCUMENT}"
    archive_marker = f"campaigns/{slug}/{_ARCHIVE_MARKER}"
    documents = store.read_many(tenant, [goal_document, archive_marker])
    if goal_document not in documents:
        return None
    live = registry.active_for_campaign(tenant, slug)
    return _CampaignRecord(
        slug=slug,
        goal=_named_goal(documents[goal_document], slug),
        latest=deliverables.latest_by_campaign(tenant, [slug]).get(slug, {}),
        archived=archive_marker in documents,
        halted=live if live is not None and live.status in HELD_STATUSES else None,
    )


async def _require_campaign(tenant: str, slug: str) -> _CampaignRecord:
    """Read a campaign the caller's tenant owns, off the event loop, or 404.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        The campaign as stored.

    Raises:
        HTTPException: 404 if the caller's tenant has no such campaign.
    """
    record = await asyncio.to_thread(
        _read_campaign, tenant, slug, get_document_store(), get_deliverable_store(), get_registry()
    )
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No such campaign '{slug}'."))
    return record


async def _describe_campaign(tenant: str, record: _CampaignRecord) -> dict[str, object]:
    """Describe one campaign: its goal, its lifecycle status, and every stage.

    Args:
        tenant: The tenant that owns the campaign.
        record: The campaign as read from the stores.

    Returns:
        The campaign as the interface reads it.
    """
    stages, status = await _stage_report(tenant, record)
    return {
        "id": record.slug,
        **record.goal.model_dump(),
        "status": ARCHIVED if record.archived else status,
        "stages": stages,
    }


async def _stage_report(
    tenant: str, record: _CampaignRecord
) -> tuple[list[dict[str, object]], str]:
    """Report a campaign's stages and lifecycle status as the interface reads them.

    Where the campaign has got to is derived in
    :mod:`marketing_os.campaign.progress` from data already read; this only
    renders those values as the contract's shapes.

    Args:
        tenant: The tenant that owns the campaign.
        record: The campaign as read from the stores.

    Returns:
        The stages in pipeline order, and the campaign's lifecycle status.
    """
    hold = await _hold_of(tenant, record.halted) if record.halted else None
    progress = progress_from_latest(
        record.latest,
        human_gate_stages=get_settings().human_gate_stages,
        hold=hold,
    )
    return [_render_stage(stage) for stage in progress.stages], progress.status


@app.post("/campaigns", status_code=201)
async def create_campaign(body: CreateCampaign, identity: Identity) -> dict[str, object]:
    """Create a campaign from its goal and return it, in ``draft``.

    The goal is written as the canonical ``goal.md`` every specialist reads, so a
    campaign created through the interface is gated exactly as a hand-authored
    one is — and passes, since the Required fields were collected here.

    Args:
        body: The campaign goal.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The created campaign.

    Raises:
        HTTPException: 422 if a Required field is missing or the segment is not
            one the tenant's Brand DNA names.
    """
    tenant = identity.tenant_id
    goal = CampaignGoal(**body.model_dump())

    missing = missing_goal_fields(goal)
    if missing:
        raise _http_error(
            ValidationError("The campaign goal is incomplete. Missing: " + ", ".join(missing) + ".")
        )

    slug = await asyncio.to_thread(_write_new_campaign, tenant, goal, get_document_store())
    created = _CampaignRecord(slug=slug, goal=goal, latest={}, archived=False, halted=None)
    return await _describe_campaign(tenant, created)


def _write_new_campaign(tenant: str, goal: CampaignGoal, store: DocumentStore) -> str:
    """Allocate a slug for a goal and write it as the campaign's goal document.

    The segment check, the slug listing and the write are all synchronous store
    calls, gathered here so the caller runs them off the event loop together.
    The campaign this creates has produced nothing, is not archived and has no
    run, so nothing is read back to describe it.

    Args:
        tenant: The tenant that owns the campaign.
        goal: The complete campaign goal.
        store: The tenant-scoped document store.

    Returns:
        The slug the campaign was given.

    Raises:
        HTTPException: 422 if the segment is not one the tenant's Brand DNA
            names.
    """
    _require_known_segment(tenant, goal.audience_segment, store)
    slug = allocate_slug(goal.name, taken=_campaign_slugs(tenant, store))
    store.write(tenant, f"campaigns/{slug}/{_GOAL_DOCUMENT}", render_campaign_goal(goal))
    return slug


def _require_known_segment(tenant: str, segment: str, store: DocumentStore) -> None:
    """Refuse a target segment the tenant's Brand DNA does not name.

    A campaign targets one of the segments the business described, never free
    text — the whole pipeline grounds its work in that segment, so inventing one
    would ground it in nothing (the Brand DNA rule).

    Args:
        tenant: The tenant that owns the campaign.
        segment: The segment the campaign targets.
        store: The tenant-scoped document store.

    Raises:
        HTTPException: 422 if the segment is not one the Brand DNA names.
    """
    defined = (
        audience_segments(store.read(tenant, DNA_DOCUMENT))
        if store.exists(tenant, DNA_DOCUMENT)
        else []
    )
    known = [defined_segment.title for defined_segment in defined]
    if segment not in known:
        named = ", ".join(known) if known else "none yet — complete your Brand DNA first"
        raise _http_error(
            ValidationError(
                f"audience_segment must be one your Brand DNA names ({named}), not '{segment}'."
            )
        )


@app.get("/campaigns")
async def list_campaigns(identity: Identity) -> dict[str, object]:
    """List the tenant's active campaigns with lifecycle status and stage progress.

    Archived campaigns are left out: archiving is what takes a campaign off this
    list, and reading it back is what ``GET /campaigns/{slug}`` is for.

    The whole portfolio is read in a bounded number of queries rather than a
    fan-out per campaign, and the reads run in a worker thread: the stores are
    synchronous, so a hundred-campaign list left on the event loop would hold up
    every other request to the engine behind it.

    Args:
        identity: The verified identity whose tenant owns the campaigns.

    Returns:
        One summary per active campaign.
    """
    tenant = identity.tenant_id
    portfolio = await asyncio.to_thread(
        _read_portfolio, tenant, get_document_store(), get_deliverable_store(), get_registry()
    )
    holds_by_slug = await _holds_by_slug(tenant, portfolio.halted)
    human_gate_stages = get_settings().human_gate_stages

    summaries: list[dict[str, object]] = []
    for slug in portfolio.slugs:
        progress = progress_from_latest(
            portfolio.latest.get(slug, {}),
            human_gate_stages=human_gate_stages,
            hold=holds_by_slug.get(slug),
        )
        stages = [_render_stage(stage) for stage in progress.stages]
        goal = portfolio.goals[slug]
        summaries.append(
            {
                "id": slug,
                "name": goal.name,
                "objective": goal.objective,
                "status": progress.status,
                "stage_progress": _stage_progress(stages),
                "blocked_reason": _blocked_reason(stages, progress.status),
            }
        )
    return {"campaigns": summaries}


@dataclass(frozen=True)
class _Portfolio:
    """One tenant's active campaigns, read in a bounded number of queries.

    Attributes:
        slugs: The active campaign slugs, sorted, archived ones already excluded.
        goals: Each active campaign's goal, keyed by slug.
        latest: Each campaign's newest deliverable version per stage, keyed by
            slug then stage key; a campaign that has produced nothing is absent.
        halted: The listed campaigns' live runs that are holding on a person,
            at an Approval Gate or for an answer. What each is holding for is a
            checkpoint read, not a store read, so it is resolved by the caller.
    """

    slugs: list[str]
    goals: dict[str, CampaignGoal]
    latest: dict[str, dict[str, DeliverableVersion]]
    halted: list[RunRecord]


def _read_portfolio(
    tenant: str, store: DocumentStore, deliverables: DeliverableStore, registry: RunRegistry
) -> _Portfolio:
    """Read everything the campaign list needs, in a fixed number of queries.

    Four reads whatever the number of campaigns: one listing of the tenant's
    campaign documents, which names both the goals and the archive markers; one
    bulk read of those goals; one bulk read of every campaign's newest
    deliverable per stage; and one read of the tenant's live runs. Every one of
    them is a synchronous store call, so they are gathered here for the caller to
    run off the event loop together — a read left behind would stall the engine
    exactly as the whole fan-out used to.

    Args:
        tenant: The tenant whose campaigns are listed.
        store: The tenant-scoped document store.
        deliverables: The store holding each stage's version chain.
        registry: The registry naming which campaigns have a live run.

    Returns:
        The tenant's active campaigns and the data every summary is derived from.
    """
    paths = store.list(tenant, "campaigns")
    archived = _archived_slugs_in(paths)
    slugs = [slug for slug in _slugs_in(paths) if slug not in archived]
    documents = store.read_many(tenant, [f"campaigns/{slug}/{_GOAL_DOCUMENT}" for slug in slugs])
    goals = {
        slug: _named_goal(document, slug)
        for slug in slugs
        if (document := documents.get(f"campaigns/{slug}/{_GOAL_DOCUMENT}")) is not None
    }
    listed = sorted(goals)
    return _Portfolio(
        slugs=listed,
        goals=goals,
        latest=deliverables.latest_by_campaign(tenant, listed),
        halted=[
            record
            for record in registry.active(tenant)
            if record.status in HELD_STATUSES and record.slug in goals
        ],
    )


async def _holds_by_slug(tenant: str, halted: list[RunRecord]) -> dict[str, RunHold]:
    """Return what each halted run is holding for, keyed by campaign.

    Only runs already known to be waiting on a person cost a checkpoint read, and
    one campaign holds at most one run (ADR-0025), so this is bounded by how many
    of the tenant's campaigns are holding rather than by how many exist.

    Args:
        tenant: The tenant that owns the campaigns.
        halted: The tenant's live runs that are holding on a person.

    Returns:
        The hold per campaign, with idle campaigns absent.
    """
    holds: dict[str, RunHold] = {}
    for record in halted:
        hold = await _hold_of(tenant, record)
        if hold is not None:
            holds[record.slug] = hold
    return holds


async def _hold_of(tenant: str, halted: RunRecord) -> RunHold | None:
    """Return what a halted run is holding for: which stage, and a decision or an answer.

    Read from the checkpoint, the same durable source the approve, revise and
    clarification endpoints consult, so the stepper cannot disagree with what
    those endpoints will accept — and so the answer holds when run tracing is
    switched off.

    Args:
        tenant: The tenant that owns the campaign.
        halted: The live run that is holding on a person.

    Returns:
        The hold, or ``None`` when the checkpoint shows none.
    """
    return await pending_hold(
        tenant, halted.slug, stage=halted.stage, checkpointer=get_checkpointer()
    )


def _stage_progress(stages: list[dict[str, object]]) -> dict[str, object]:
    """Summarise how far a campaign has got through the pipeline.

    Args:
        stages: The campaign's stages in pipeline order.

    Returns:
        How many stages have completed, how many there are, and the stage the
        campaign is currently on — the first that has not completed.
    """
    completed = [stage for stage in stages if stage["state"] == "completed"]
    current = next((stage for stage in stages if stage["state"] != "completed"), None)
    return {
        "completed": len(completed),
        "total": len(stages),
        "current_stage_key": current["key"] if current else None,
    }


def _blocked_reason(stages: list[dict[str, object]], status: str) -> str | None:
    """Say what is holding a campaign up, in the operator's language.

    Args:
        stages: The campaign's stages in pipeline order.
        status: The campaign's lifecycle status.

    Returns:
        The reason, or ``None`` when nothing is blocking the campaign.
    """
    if status == AWAITING_APPROVAL:
        waiting = next((stage for stage in stages if stage["state"] == AWAITING_APPROVAL), None)
        phase = waiting["phase"] if waiting else "A stage"
        return f"{phase} is waiting for your approval."
    if status == AWAITING_CLARIFICATION:
        asking = next((stage for stage in stages if stage["state"] == AWAITING_CLARIFICATION), None)
        phase = asking["phase"] if asking else "A stage"
        return f"{phase} has a question for you."
    stale = [stage for stage in stages if stage["stale"]]
    if stale:
        return f"{stale[0]['phase']} rests on a decision you have since re-opened."
    return None


@app.get("/campaigns/{slug}")
async def get_campaign(slug: str, identity: Identity) -> dict[str, object]:
    """Read one campaign: its goal fields, lifecycle status, and per-stage state.

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The campaign.

    Raises:
        HTTPException: 404 if the caller's tenant has no such campaign.
    """
    tenant = identity.tenant_id
    record = await _require_campaign(tenant, slug)
    return await _describe_campaign(tenant, record)


@app.post("/campaigns/{slug}/archive")
async def archive_campaign(slug: str, identity: Identity) -> dict[str, object]:
    """Archive a campaign, taking it off the active list.

    Archiving is a lifecycle change, not a deletion: the goal and every
    deliverable stay readable, because a business that ran a campaign should be
    able to look at what it decided.

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The archived campaign.

    Raises:
        HTTPException: 404 if the caller's tenant has no such campaign.
    """
    tenant = identity.tenant_id
    record = await _require_campaign(tenant, slug)
    await asyncio.to_thread(
        get_document_store().write,
        tenant,
        f"campaigns/{slug}/{_ARCHIVE_MARKER}",
        "Archived. The campaign and its deliverables stay readable.\n",
    )
    return await _describe_campaign(tenant, replace(record, archived=True))


@app.get("/brand-dna/segments")
def brand_dna_segments(identity: Identity) -> dict[str, object]:
    """List the audience segments a campaign may target.

    The segments come from the tenant's Brand DNA, so the interface offers
    exactly what the business described rather than a free-text box.

    Each segment carries its title and its description, because the two together
    are what lets a business tell one group from another when it picks; only the
    title identifies the segment a campaign targets.

    Args:
        identity: The verified identity whose tenant owns the Brand DNA.

    Returns:
        The segments the Brand DNA defines, in the order the business listed
        them.
    """
    store = get_document_store()
    tenant = identity.tenant_id
    if not store.exists(tenant, DNA_DOCUMENT):
        return {"segments": []}
    segments = audience_segments(store.read(tenant, DNA_DOCUMENT))
    return {"segments": [segment.model_dump() for segment in segments]}


@app.get("/campaigns/{slug}/gate")
def gate(slug: str, identity: Identity) -> dict[str, object]:
    """Return the Stage 0 gate report for a campaign.

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The gate status and any issues.
    """
    settings = get_settings()
    report = check_gate(
        settings,
        identity.tenant_id,
        slug,
        store=get_document_store(),
        questionnaire=get_questionnaire_store().published(),
    )
    return {"ok": report.ok, "issues": report.all_issues}


@app.get("/campaigns/{slug}/deliverables")
def deliverables(slug: str, identity: Identity) -> dict[str, object]:
    """List the deliverable documents written for a campaign.

    The listing goes through the tenant-scoped document store, so a slug owned
    by another tenant is simply absent — indistinguishable from one that was
    never created.

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The campaign slug, the list of written documents, and one entry per
        stage that has produced a deliverable carrying its latest version and
        whether it is stale — so the interface can flag superseded work at a
        glance rather than one deliverable-read at a time.

    Raises:
        HTTPException: 404 if the caller's tenant has no such campaign.
    """
    tenant = identity.tenant_id
    store = get_document_store()
    documents = store.list(tenant, f"campaigns/{slug}")
    if not documents:
        raise _http_error(DocumentNotFoundError(f"No campaign '{slug}'"))
    files = [
        {"name": document.rsplit("/", 1)[-1], "path": document}
        for document in documents
        if document.endswith(".md")
    ]
    return {"slug": slug, "files": files, "deliverables": _deliverable_summaries(tenant, slug)}


def _deliverable_summaries(tenant: str, slug: str) -> list[dict[str, object]]:
    """Summarise every deliverable a campaign has produced, with its staleness.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        One entry per produced deliverable in pipeline order, each with its
        stage key, latest version, staleness, and when it was last written.
    """
    return [
        {
            "stage_key": produced.stage_key,
            "latest_version": produced.latest.version,
            "stale": produced.stale,
            "updated_at": produced.latest.created_at,
        }
        for produced in produced_deliverables(get_deliverable_store(), tenant, slug)
    ]


@app.get("/campaigns/{slug}/deliverables/{name}")
def deliverable(slug: str, name: str, identity: Identity) -> dict[str, object]:
    """Return one deliverable's markdown content.

    Args:
        slug: The campaign slug.
        name: The deliverable filename, e.g. ``research.md``.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The deliverable's name, path, and full markdown content.

    Raises:
        HTTPException: 404 if the caller's tenant has no such deliverable.
    """
    document = f"campaigns/{slug}/{name}"
    tenant = identity.tenant_id
    store = get_document_store()
    if not name.endswith(".md") or not store.exists(tenant, document):
        raise _http_error(DocumentNotFoundError(f"No deliverable '{name}' for campaign '{slug}'"))
    stage_key = _stage_key_for(name)
    return {
        "name": name,
        "path": document,
        "stage_key": stage_key,
        "stale": stage_key in stale_keys(get_deliverable_store(), tenant, slug),
        "content": store.read(tenant, document),
    }


@app.get("/campaigns/{slug}/stages")
async def stages(slug: str, identity: Identity) -> dict[str, object]:
    """Report each pipeline stage with its approval policy and where it has got to.

    The approval policy is reported alongside the stage so the interface can say
    which stages the system handles itself and which will stop and ask — before
    the run starts, not when it halts (ADR-0015). A stage whose input was
    re-opened since it ran reads ``stale``, which is how the interface shows that
    work rests on a superseded decision rather than quietly rendering it as done.

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The campaign slug, its lifecycle status, and its stages in mandatory
        pipeline order, each with its key, operator Phase, state, approval
        policy, and latest deliverable version if it has one.

    Raises:
        HTTPException: 404 if the caller's tenant has no such campaign.
    """
    tenant = identity.tenant_id
    record = await _require_campaign(tenant, slug)
    reported, status = await _stage_report(tenant, record)
    return {"slug": slug, "status": status, "stages": reported}


def _render_stage(progress: StageProgress) -> dict[str, object]:
    """Render one stage's progress as the contract's stage object.

    The phase is what the operator's stepper groups by, so the interface renders
    its designed steps without the engine adopting UI vocabulary (ADR-0017).

    Args:
        progress: How far the stage has got.

    Returns:
        The stage's key, phase, state, approval policy, latest version, and
        whether it rests on a superseded decision.
    """
    return {
        "key": progress.stage.key,
        "phase": progress.stage.phase,
        "state": progress.state,
        "approval_policy": progress.stage.approval_policy,
        "latest_version": progress.latest.version if progress.latest else None,
        "stale": progress.stale,
    }


@app.get("/campaigns/{slug}/deliverables/{name}/versions")
def deliverable_versions(slug: str, name: str, identity: Identity) -> dict[str, object]:
    """List a deliverable's versions, newest first.

    Each entry names the feedback that produced it and whether that feedback came
    from a person or the QA reviewer, so the history explains itself months later
    (ADR-0015).

    Args:
        slug: The campaign slug.
        name: The deliverable filename, e.g. ``brand-strategy.md``.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The stage key and its version summaries, newest first.

    Raises:
        HTTPException: 404 if the caller's tenant has no such deliverable.
    """
    stage_key = _stage_key_for(name)
    history = get_deliverable_store().history(identity.tenant_id, slug, stage_key)
    if not history:
        raise _http_error(DocumentNotFoundError(f"No deliverable '{name}' for campaign '{slug}'"))
    return {
        "slug": slug,
        "stage_key": stage_key,
        "versions": [version.model_dump(exclude={"content"}) for version in history],
    }


@app.get("/campaigns/{slug}/deliverables/{name}/versions/{version}")
def deliverable_version(
    slug: str, name: str, version: int, identity: Identity
) -> dict[str, object]:
    """Return one historical version of a deliverable, with the feedback behind it.

    Args:
        slug: The campaign slug.
        name: The deliverable filename, e.g. ``brand-strategy.md``.
        version: The version number to read.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The version's full content, feedback, and the version it supersedes.

    Raises:
        HTTPException: 404 if the caller's tenant has no such version.
    """
    stage_key = _stage_key_for(name)
    store = get_deliverable_store()
    stored = store.version(identity.tenant_id, slug, stage_key, version)
    if stored is None:
        raise _http_error(
            DocumentNotFoundError(f"No version {version} of '{name}' for campaign '{slug}'")
        )
    latest = store.latest(identity.tenant_id, slug, stage_key)
    return {
        "slug": slug,
        **stored.model_dump(),
        "latest": latest is not None and latest.version == stored.version,
    }


def _stage_key_for(name: str) -> str:
    """Return the pipeline stage a deliverable filename belongs to.

    Args:
        name: The deliverable filename, e.g. ``brand-strategy.md``.

    Returns:
        The stage key.

    Raises:
        HTTPException: 404 if no pipeline stage writes that filename — an
            unknown name is absent, not a server error.
    """
    for stage in PIPELINE:
        if stage.deliverable == name:
            return stage.key
    raise _http_error(DocumentNotFoundError(f"No deliverable '{name}'"))


@app.post("/campaigns/{slug}/run", status_code=202)
async def run(slug: str, body: RunCampaign, identity: Identity) -> dict[str, object]:
    """Start a detached background run and return its ``run_id`` immediately.

    The run is a first-class background job: it executes as an :class:`asyncio.Task`
    on the async graph path (ADR-0009), held in the process run registry keyed by
    slug. This endpoint no longer blocks on the pipeline — observe the run via
    :func:`get_run_status` (``GET /runs/{run_id}``) or the stream endpoint. The
    Stage 0 gate is checked synchronously so a misconfigured campaign fails fast
    rather than spawning a job that would immediately halt.

    Args:
        slug: The campaign slug.
        body: The run request.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The new run's id, slug, stage, and initial ``running`` status.

    Raises:
        HTTPException: 402 if the tenant's credits are spent; 409 if the gate
            failed, the slug already has an active run, or the campaign has been
            run its allowed number of times.
    """
    settings = get_settings()
    store = get_document_store()
    tenant = identity.tenant_id
    report = check_gate(
        settings, tenant, slug, store=store, questionnaire=get_questionnaire_store().published()
    )
    if not report.ok:
        raise _http_error(GateError("Stage 0 gate failed", missing=report.all_issues))
    _refuse_when_quota_spent(tenant)
    _refuse_when_runs_spent(tenant, slug)
    run_id = new_run_id()

    async def launch() -> CampaignResult:
        """Execute the background run to completion on the async graph path.

        Returns:
            The structured campaign result.
        """
        return await arun_campaign(
            settings,
            tenant,
            slug,
            stage=body.stage,
            run_id=run_id,
            checkpointer=get_checkpointer(),
            document_store=store,
            deliverable_store=get_deliverable_store(),
            usage_ledger=get_usage_ledger(),
            questionnaire=get_questionnaire_store().published(),
        )

    try:
        get_registry().start(
            run_id=run_id,
            slug=slug,
            stage=body.stage,
            tenant=tenant,
            user_id=identity.user_id,
            launch=launch,
        )
    except RunConflictError as exc:
        raise _http_error(exc) from exc
    return {"run_id": run_id, "slug": slug, "stage": body.stage, "status": RUNNING}


async def _release_gate_held_by(identity: VerifiedIdentity, slug: str) -> None:
    """Free a campaign whose only claim is the caller's own run waiting at a gate.

    Re-opening an earlier decision **is** a decision about the pending one: the
    owner has stopped caring what the gate is asking and wants to change
    something upstream instead. Leaving that halted run holding the campaign
    would refuse them their own campaign until they separately cancelled a run
    they have already moved on from.

    Only a run holding on a person — at a gate, or for an answer to a
    specialist's question — is released, and only the caller's own. A run that
    is genuinely executing is left alone, so re-opening still refuses a
    campaign someone is actively working on rather than pulling the work out
    from under it.

    Args:
        identity: The verified identity re-opening the stage.
        slug: The campaign slug.
    """
    registry = get_registry()
    held = registry.active_for_campaign(identity.tenant_id, slug)
    if held is None or held.status not in HELD_STATUSES:
        return
    if held.user_id and held.user_id != identity.user_id:
        return
    await registry.cancel(held.run_id, identity.tenant_id, identity.user_id)
    _LOGGER.info("run.released_for_reopen run_id=%s slug=%s", held.run_id, slug)


class ReopenStage(BaseModel):
    """Request body for re-opening a stage the business owner already approved.

    Attributes:
        feedback: What they want changed, now that they have changed their mind.
            Required: re-opening with nothing to act on would re-run the stage
            identically and charge for it.
    """

    feedback: str


@app.post("/campaigns/{slug}/stages/{stage_key}/reopen", status_code=202)
async def reopen_stage(
    slug: str, stage_key: str, body: ReopenStage, identity: Identity
) -> dict[str, object]:
    """Re-open an approved stage to revise it; everything downstream goes stale.

    A campaign gets edited weeks later, after work has been built on top of it.
    Re-opening runs **only the named stage**, seeded with the owner's feedback
    and the deliverable they are reacting to. Every downstream deliverable then
    reads ``stale``: it is flagged, not regenerated, and no model is called on
    its behalf until the owner re-runs it themselves (ADR-0015). Auto-re-running
    was rejected — it would spend tokens and image budget redoing work nobody
    asked to have redone — so the inconsistency is made visible and left the
    owner's to resolve.

    The stage's checkpoint thread is cleared first, so a re-open starts the stage
    afresh rather than resuming whatever a previous re-open of it left halted.

    Args:
        slug: The campaign slug.
        stage_key: The stage to re-open.
        body: The feedback to re-run the stage with.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The new run's id, slug, re-opened stage, and initial ``running`` status.

    Raises:
        HTTPException: 404 if the caller's tenant has no such stage deliverable;
            402 if the tenant's credits are spent; 409 if the gate fails, the
            campaign already has an active run, or a cap is spent; 422 if the
            feedback is empty.
    """
    feedback = body.feedback.strip()
    if not feedback:
        raise _http_error(ValidationError("Say what you want changed."))
    if stage_key not in PIPELINE_BY_KEY:
        raise _http_error(DocumentNotFoundError(f"No stage '{stage_key}'"))
    tenant = identity.tenant_id
    settings = get_settings()
    store = get_document_store()
    if get_deliverable_store().latest(tenant, slug, stage_key) is None:
        raise _http_error(
            DocumentNotFoundError(f"Stage '{stage_key}' has produced nothing for '{slug}'")
        )
    report = check_gate(
        settings, tenant, slug, store=store, questionnaire=get_questionnaire_store().published()
    )
    if not report.ok:
        raise _http_error(GateError("Stage 0 gate failed", missing=report.all_issues))
    _refuse_when_revisions_spent(tenant, slug, stage_key)
    _refuse_when_quota_spent(tenant)
    _refuse_when_runs_spent(tenant, slug)
    await _release_gate_held_by(identity, slug)
    run_id = new_run_id()

    async def launch() -> CampaignResult:
        """Re-run the single re-opened stage with the owner's feedback.

        Returns:
            The structured campaign result.
        """
        return await arun_campaign(
            settings,
            tenant,
            slug,
            stage=stage_key,
            run_id=run_id,
            checkpointer=get_checkpointer(),
            document_store=store,
            deliverable_store=get_deliverable_store(),
            usage_ledger=get_usage_ledger(),
            questionnaire=get_questionnaire_store().published(),
            feedback=feedback,
        )

    try:
        get_registry().start(
            run_id=run_id,
            slug=slug,
            stage=stage_key,
            tenant=tenant,
            user_id=identity.user_id,
            launch=launch,
        )
    except RunConflictError as exc:
        raise _http_error(exc) from exc
    _LOGGER.info(
        "stage.reopened tenant=%s slug=%s stage=%s run_id=%s", tenant, slug, stage_key, run_id
    )
    return {"run_id": run_id, "slug": slug, "stage": stage_key, "status": RUNNING}


@app.get("/runs")
def list_active_runs(identity: Identity) -> dict[str, object]:
    """List the caller's runs currently in flight.

    Args:
        identity: The verified identity whose tenant owns the runs.

    Returns:
        The tenant's active runs, each with its ``run_id``, ``slug``, and ``stage``.
        Runs belonging to other tenants are not listed.
    """
    runs = [
        {"run_id": record.run_id, "slug": record.slug, "stage": record.stage}
        for record in get_registry().active(identity.tenant_id)
    ]
    return {"runs": runs}


@app.get("/runs/{run_id}")
def get_run_status(run_id: str, identity: Identity) -> dict[str, object]:
    """Report a run's lifecycle status across its five terminal and live states.

    Resolves ``running`` from the live registry, or ``completed`` / ``failed`` /
    ``cancelled`` / ``interrupted`` from the run's JSONL trace.

    Args:
        run_id: The run id to query.
        identity: The verified identity whose tenant owns the run.

    Returns:
        The run's id, slug, stage, and status.

    Raises:
        HTTPException: 404 if the caller's tenant has no such run.
    """
    status = read_run_status(get_settings(), get_registry(), run_id, identity.tenant_id)
    if status is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    return asdict(status)


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, identity: Identity) -> dict[str, object]:
    """Cancel an in-flight run, aborting its in-flight LLM call.

    Cancelling the run's task lands a :class:`asyncio.CancelledError` inside the
    specialist's awaited LLM call (ADR-0009); the trace ends with a terminal
    ``run.summary outcome=cancelled`` event and the run releases its campaign.

    The campaign's checkpoint threads are cleared too, so the next run of that
    campaign starts at stage 1. Without that, a durable checkpointer would
    resume the work the owner just cancelled (ADR-0014).

    Only the person who started a run may cancel it. A colleague's run is
    reported as absent rather than refused, so the two cases stay
    indistinguishable exactly as another tenant's does.

    Args:
        run_id: The id of the run to cancel.
        identity: The verified identity that must own the run.

    Returns:
        The cancelled run's id, slug, and ``cancelled`` status.

    Raises:
        HTTPException: 404 if the caller's tenant has no live run with that id.
    """
    cancelled = await get_registry().cancel(run_id, identity.tenant_id, identity.user_id)
    if cancelled is None:
        raise _http_error(DocumentNotFoundError(f"No active run '{run_id}'"))
    return {"run_id": run_id, "slug": cancelled.slug, "status": CANCELLED}


class ApproveStage(BaseModel):
    """Request body for approving the stage waiting at an Approval Gate.

    The stage is named rather than implied, so an approval always applies to the
    deliverable the person actually read — never to whatever the run happened to
    advance to while they were reading (ADR-0015).

    Attributes:
        stage_key: The stage being approved.
    """

    stage_key: str


class ReviseStage(BaseModel):
    """Request body for sending the waiting stage back with written feedback.

    Attributes:
        stage_key: The stage being sent back.
        feedback: What the business owner wants changed; recorded on the new
            version this produces.
    """

    stage_key: str
    feedback: str


async def _resume_run(
    run_id: str, identity: VerifiedIdentity, decision: ApprovalDecision
) -> dict[str, object]:
    """Resume a run halted at an Approval Gate with a person's decision.

    The same run continues on its existing checkpoint thread, so approving is
    one action rather than "start a second run and hope it picks up where the
    first stopped" (ADR-0015).

    **The checkpoint is authoritative** about whether a gate is waiting, because
    it is the thing the resume actually answers; the run store only records what
    a process last observed. When the two disagree — a startup sweep that raced a
    halt, say — a run with a live gate is re-marked ``awaiting_approval`` and the
    approval proceeds, rather than the owner being told nothing is waiting for a
    decision that plainly is.

    Args:
        run_id: The halted run to resume.
        identity: The verified identity that must own the run.
        decision: What the person decided at the gate.

    Returns:
        The resumed run's id, slug, and ``running`` status.

    Raises:
        HTTPException: 404 if the caller has no run with that id; 409 if the
            named stage is not the one holding the run.
    """
    record = get_registry().get(run_id, identity.tenant_id)
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    waiting = await awaiting_approval_stage(
        record.tenant_id, record.slug, stage=record.stage, checkpointer=get_checkpointer()
    )
    if waiting != decision.stage_key:
        raise _http_error(StageNotAwaitingApprovalError(decision.stage_key))
    await _relaunch(
        record,
        identity,
        held_as=AWAITING_APPROVAL,
        resume=decision.model_dump(),
        refusal=StageNotAwaitingApprovalError(decision.stage_key),
    )
    return {"run_id": run_id, "slug": record.slug, "stage": decision.stage_key, "status": RUNNING}


async def _relaunch(
    record: RunRecord,
    identity: VerifiedIdentity,
    *,
    held_as: str,
    resume: dict[str, object],
    refusal: MarketingOSError,
    save: Callable[[], None] | None = None,
) -> None:
    """Continue a halted run on its own checkpoint thread with what a person supplied.

    Shared by approving, revising and answering: each has already confirmed,
    from the checkpoint, that the run is holding for exactly that (ADR-0015,
    ADR-0028). What is left is the same for all three — bring the run store
    back into line if it disagrees with the checkpoint, and resume the run.

    The run store is read again here, after the checkpoint read the caller
    awaited, and everything from that read to the resume is synchronous. The
    service is one event loop, so nothing else can resume the same run inside
    that window — which is what lets ``save`` write the answers with no risk
    of a second submission, or a colleague's, writing them too: anything that
    does not pass is refused before the save runs.

    Args:
        record: The run's record, as the caller read it before its checkpoint read.
        identity: The verified identity resuming the run.
        held_as: The status the record should be holding at, given what the
            checkpoint says: ``awaiting_approval`` or ``awaiting_clarification``.
        resume: The payload the pending ``interrupt()`` returns with.
        refusal: The error to answer with when the run turns out not to be
            resumable after all — it finished, or another request resumed it.
        save: What to record before the run continues, if anything; the
            answers to a clarification, which the resumed stage reads.

    Raises:
        HTTPException: ``refusal`` when the run cannot be resumed; 404 when the
            caller does not hold it — a colleague's run reads as absent, exactly
            as cancelling does.
    """
    settings = get_settings()
    registry = get_registry()
    run_id = record.run_id
    tenant = record.tenant_id
    slug = record.slug
    current = registry.get(run_id, tenant)
    if current is None or (current.user_id and current.user_id != identity.user_id):
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    if current.status != held_as:
        if current.status != record.status:
            raise _http_error(refusal)
        _LOGGER.warning(
            "run.hold_out_of_sync run_id=%s slug=%s recorded=%s checkpoint=%s",
            run_id,
            slug,
            current.status,
            held_as,
        )
        if registry.mark_held(run_id, tenant, held_as) is None:
            raise _http_error(refusal)
    if save is not None:
        save()

    async def relaunch() -> CampaignResult:
        """Continue the halted run from where it is holding.

        Returns:
            The structured campaign result.
        """
        return await arun_campaign(
            settings,
            tenant,
            slug,
            stage=record.stage,
            run_id=run_id,
            checkpointer=get_checkpointer(),
            document_store=get_document_store(),
            deliverable_store=get_deliverable_store(),
            usage_ledger=get_usage_ledger(),
            questionnaire=get_questionnaire_store().published(),
            resume=Command(resume=resume),
        )

    resumed = registry.resume(
        run_id=run_id, tenant=tenant, user_id=identity.user_id, launch=relaunch
    )
    if resumed is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))


@app.post("/runs/{run_id}/approve")
async def approve_stage(run_id: str, body: ApproveStage, identity: Identity) -> dict[str, object]:
    """Approve the stage waiting at the gate; the run resumes into the next stage.

    Args:
        run_id: The halted run.
        body: The approval, naming the stage being approved.
        identity: The verified identity that must own the run.

    Returns:
        The resumed run's id, slug, approved stage, and ``running`` status.

    Raises:
        HTTPException: 404 if the caller has no such run; 409 if the named stage
            is not awaiting approval.
    """
    decision = ApprovalDecision(stage_key=body.stage_key, approved=True)
    return await _resume_run(run_id, identity, decision)


@app.post("/runs/{run_id}/revise", status_code=202)
async def revise_stage(run_id: str, body: ReviseStage, identity: Identity) -> dict[str, object]:
    """Send the waiting stage back with feedback, producing a new version.

    Nothing is overwritten: the re-run appends a new version of the deliverable
    carrying this feedback, and the version the person refused stays readable
    (ADR-0015).

    Args:
        run_id: The halted run.
        body: The refusal, naming the stage and the feedback to re-run with.
        identity: The verified identity that must own the run.

    Returns:
        The resumed run's id, slug, re-running stage, and ``running`` status.

    Raises:
        HTTPException: 404 if the caller has no such run; 402 if the tenant's
            credits are spent; 409 if the named stage is not awaiting approval,
            or its revision cap is spent; 422 if the feedback is empty — a
            refusal with nothing to act on would re-run the stage identically
            and charge for it.
    """
    feedback = body.feedback.strip()
    if not feedback:
        raise _http_error(ValidationError("Say what you want changed."))
    record = get_registry().get(run_id, identity.tenant_id)
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    _refuse_when_revisions_spent(identity.tenant_id, record.slug, body.stage_key)
    _refuse_when_quota_spent(identity.tenant_id)
    decision = ApprovalDecision(stage_key=body.stage_key, approved=False, feedback=feedback)
    return await _resume_run(run_id, identity, decision)


@app.get("/runs/{run_id}/clarifications")
async def run_clarifications(run_id: str, identity: Identity) -> dict[str, object]:
    """Read the questions a halted run is asking the business, with their reasons.

    Read from the checkpoint, the one place a hold stays true across a restart,
    so the screen that lists the questions shows exactly what the run will be
    resumed with (ADR-0028).

    Args:
        run_id: The halted run.
        identity: The verified identity that must own the run.

    Returns:
        The run's id, slug, the stage that asked, and its questions.

    Raises:
        HTTPException: 404 if the caller has no such run; 409 if the run is not
            holding for a clarification — at an Approval Gate, finished, or
            still running.
    """
    record = get_registry().get(run_id, identity.tenant_id)
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    hold = await pending_hold(
        record.tenant_id, record.slug, stage=record.stage, checkpointer=get_checkpointer()
    )
    if hold is None or hold.kind != CLARIFICATION_HOLD:
        raise _http_error(RunNotAwaitingClarificationError(run_id))
    return {
        "run_id": run_id,
        "slug": record.slug,
        "stage": hold.stage,
        "questions": [question.model_dump() for question in hold.questions],
    }


class ClarificationAnswer(BaseModel):
    """One answer to one question a halted run is asking.

    Attributes:
        question: The question, exactly as the run asked it. A specialist's
            question has no id, so its text is what pairs the answer to it.
        answer: The owner's answer, in their own words.
    """

    question: str
    answer: str


class AnswerClarifications(BaseModel):
    """Request body for answering every question a halted run is asking.

    All of a stage's questions are answered together, because the stage re-runs
    once from a Brand DNA that carries every answer (ADR-0028); answering one
    and leaving another would re-run it on a guess.

    Attributes:
        answers: One answer per pending question. A blank answer counts as no
            answer, so the one rule — every question needs one — is checked in
            one place, where the answers meet the questions.
    """

    answers: list[ClarificationAnswer]


def _clarifications_from(
    hold: RunHold, answers: list[ClarificationAnswer], slug: str
) -> list[Clarification]:
    """Pair the owner's answers with the questions the run is holding for.

    Args:
        hold: What the run is asking, read from its checkpoint.
        answers: The owner's answers, one per question.
        slug: The campaign the stage was working on when it asked.

    Returns:
        The Clarifications to record, in the order the questions were asked.

    Raises:
        ValidationError: If an answer names a question the run did not ask, or
            a question the run asked was left unanswered or answered blank.
    """
    asked = {question.question.strip(): question for question in hold.questions}
    given = {item.question.strip(): item.answer.strip() for item in answers if item.answer.strip()}
    unknown = sorted(set(given) - set(asked))
    if unknown:
        raise ValidationError(f"The run did not ask: {'; '.join(unknown)}")
    unanswered = [text for text in asked if text not in given]
    if unanswered:
        raise ValidationError(
            f"Every question needs an answer. Unanswered: {'; '.join(unanswered)}"
        )
    answered_at = now_iso()
    return [
        Clarification(
            id=f"clr_{uuid4().hex}",
            question=question.question,
            reason=question.reason,
            answer=given[text],
            stage=hold.stage,
            slug=slug,
            answered_at=answered_at,
        )
        for text, question in asked.items()
    ]


@app.post("/runs/{run_id}/clarifications", status_code=202)
async def answer_clarifications(
    run_id: str, body: AnswerClarifications, identity: Identity
) -> dict[str, object]:
    """Answer a halted run's questions; the answers join the Brand DNA and the run continues.

    Each answer is saved as a Clarification — part of the business's Brand DNA,
    under its own section, never Required — and the DNA markdown is re-rendered
    before the run resumes, so the stage re-enters seeded with the facts it
    asked for. Every later campaign reads the same DNA, so the same fact is
    asked for once (ADR-0028). The run continues through the same mechanism an
    approval uses: the same run id, claim and checkpoint thread.

    Args:
        run_id: The halted run.
        body: One answer per pending question.
        identity: The verified identity that must own the run.

    Returns:
        The resumed run's id, slug, the stage re-running, and ``running`` status.

    Raises:
        HTTPException: 404 if the caller has no such run; 409 if the run is not
            holding for a clarification; 402 if the tenant's credits are spent,
            since the stage re-runs and that bills; 422 if a question is left
            unanswered, an answer is blank, or an answer names a question the
            run did not ask.
    """
    record = get_registry().get(run_id, identity.tenant_id)
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    hold = await pending_hold(
        record.tenant_id, record.slug, stage=record.stage, checkpointer=get_checkpointer()
    )
    if hold is None or hold.kind != CLARIFICATION_HOLD:
        raise _http_error(RunNotAwaitingClarificationError(run_id))
    _refuse_when_quota_spent(identity.tenant_id)
    try:
        clarifications = _clarifications_from(hold, body.answers, record.slug)
    except ValidationError as exc:
        raise _http_error(exc) from exc

    def save_answers() -> None:
        """Record the answers on the Brand DNA and re-render the markdown the re-run reads."""
        updated = get_answer_store().add_clarifications(
            identity.tenant_id, clarifications=clarifications
        )
        project_brand_dna(identity, get_questionnaire_store().published(), updated)

    await _relaunch(
        record,
        identity,
        held_as=AWAITING_CLARIFICATION,
        resume={"answered": True},
        refusal=RunNotAwaitingClarificationError(run_id),
        save=save_answers,
    )
    return {"run_id": run_id, "slug": record.slug, "stage": hold.stage, "status": RUNNING}


def _refuse_when_quota_spent(tenant: str) -> None:
    """Refuse work whose first act would be a billable call the tenant cannot afford.

    Checked at the edge as well as inside the graph, and for a different reason
    than the graph's check. The graph's stops a run mid-flight; this one stops a
    run being *started* at all, so an exhausted tenant is told 402 on the request
    rather than handed a run id that immediately halts (ADR-0020).

    Args:
        tenant: The tenant the caller acts for.

    Raises:
        HTTPException: 402 once the credits are spent.
    """
    try:
        get_usage_ledger().check(tenant)
    except QuotaExhaustedError as exc:
        raise _http_error(exc) from exc


def _refuse_when_runs_spent(tenant: str, slug: str) -> None:
    """Refuse a run once a campaign has been run its allowed number of times.

    Counted from the run store rather than from process memory, so the cap holds
    across restarts and across workers — the same reasoning the per-deliverable
    revision cap follows. It bounds the *campaign*: re-opening a stage starts a
    run and is bounded here too, which is what stops a change of mind being an
    unbounded way to spend (ADR-0020).

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Raises:
        HTTPException: 409 once the cap is reached.
    """
    limit = get_settings().max_runs_per_campaign
    if len(get_registry().for_campaign(tenant, slug)) >= limit:
        raise _http_error(RunLimitError(slug, limit))


def _refuse_when_revisions_spent(tenant: str, slug: str, stage_key: str) -> None:
    """Refuse a revision once a deliverable has been sent back its allowed number of times.

    Counted from the version chain rather than from run state, because the cap is
    about the deliverable — it must hold across restarts and across separate runs
    of the same campaign, not only within one run's memory (ADR-0015). Only a
    person's revisions count, which is the same quantity the Approval Gate shows
    them: the QA reviewer's rounds have their own budget, and charging them here
    would refuse the owner's first real revision.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.
        stage_key: The deliverable being sent back.

    Raises:
        HTTPException: 409 once the cap is reached.
    """
    limit = get_settings().max_revisions
    versions = get_deliverable_store().history(tenant, slug, stage_key)
    if human_revisions_used(versions) >= limit:
        raise _http_error(RevisionLimitError(stage_key, limit))


@app.get("/campaigns/{slug}/runs")
def list_runs(slug: str, identity: Identity) -> dict[str, object]:
    """List the run-log traces recorded for a campaign.

    The list comes from the run store, so it covers runs executed by every
    worker rather than only those whose trace files happen to be on this one.
    Traces written before the store existed are appended from disk.

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The campaign slug and the available run ids (newest first).
    """
    settings = get_settings()
    tenant = identity.tenant_id
    recorded = [record.run_id for record in get_registry().for_campaign(tenant, slug)]
    on_disk = list_run_ids(settings.tenant_logs_dir(tenant), slug)
    runs = recorded + [run_id for run_id in on_disk if run_id not in recorded]
    return {"slug": slug, "runs": runs}


@app.get("/campaigns/{slug}/runs/{run_id}")
def get_run(slug: str, run_id: str, identity: Identity) -> dict[str, object]:
    """Return the parsed JSONL trace for one run.

    Args:
        slug: The campaign slug.
        run_id: The run id (trace filename without extension).
        identity: The verified identity whose tenant owns the run.

    Returns:
        The campaign slug, run id, and the list of trace events.

    Raises:
        HTTPException: 404 if the caller's tenant has no such trace.
    """
    settings = get_settings()
    path = settings.tenant_logs_dir(identity.tenant_id) / slug / f"{run_id}.jsonl"
    if not path.is_file():
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}' for campaign '{slug}'"))
    return {"slug": slug, "run_id": run_id, "events": read_events(path)}


@app.get("/runs/{run_id}/stream")
def stream_run(run_id: str, identity: Identity) -> StreamingResponse:
    """Attach to an existing run and stream its progress as Server-Sent Events.

    Observing is split from starting (the run is already executing as a detached
    background job — see ``POST /run``): this endpoint does **not** launch a run, it
    tails the run's JSONL trace. A client attaching late is replayed the events
    already recorded from the top of the trace, then followed live until the terminal
    ``run.summary`` event, at which point the stream closes. A summary that says the
    run is waiting at an Approval Gate is not terminal: the same run may be resumed
    and append more, so the stream reads through it and closes once the run is no
    longer live. Because it only reads the durable trace, any number of observers
    can attach to the same run concurrently, and a finished run replays and closes.

    Args:
        run_id: The id of the run to observe.
        identity: The verified identity whose tenant owns the run.

    Returns:
        A streaming response emitting one SSE ``data:`` frame per trace event.

    Raises:
        HTTPException: 404 if the caller's tenant has no such run.
    """
    settings = get_settings()
    registry = get_registry()
    trace_path = resolve_trace_path(settings, registry, run_id, identity.tenant_id)
    if trace_path is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))

    async def event_source() -> AsyncIterator[str]:
        """Yield each trace event as an SSE ``data:`` frame.

        Yields:
            SSE-formatted event lines.
        """
        async for event in tail_trace(
            trace_path, is_live=lambda: registry.is_live(run_id, identity.tenant_id)
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
