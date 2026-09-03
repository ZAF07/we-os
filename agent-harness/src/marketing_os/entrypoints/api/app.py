"""FastAPI service exposing the Marketing OS graph over HTTP.

Endpoints:
  GET  /health                          -> liveness; the only unauthenticated route
  GET  /me                              -> the verified identity and its tenant
  GET  /questionnaire                   -> the published question set
  GET  /brand-dna                       -> the tenant's answers and rendered markdown
  GET  /brand-dna/completeness          -> what still stands between them and a run
  POST /brand-dna/answers               -> save answers, returning the updated report
  POST /campaigns                       -> scaffold a campaign goal from the template
  GET  /campaigns/{slug}/gate           -> Stage 0 gate report
  GET  /campaigns/{slug}/deliverables   -> list written deliverables
  GET  /campaigns/{slug}/stages         -> stages with approval policy and version
  GET  /campaigns/{slug}/deliverables/{name}/versions -> a deliverable's version history
  GET  /campaigns/{slug}/deliverables/{name}/versions/{v} -> one historical version
  POST /campaigns/{slug}/run            -> start a background run, return its run_id (202)
  GET  /runs                            -> list in-flight runs
  GET  /runs/{run_id}                   -> report a run's lifecycle status
  POST /runs/{run_id}/cancel            -> cancel an in-flight run
  POST /runs/{run_id}/approve           -> approve the stage at the gate; the run resumes
  POST /runs/{run_id}/revise            -> send the stage back with feedback (new version)
  GET  /runs/{run_id}/stream            -> attach to a run and tail its trace as SSE

Every route except ``/health`` requires a verified bearer token, and the tenant
is derived from that token's claim — no operation accepts a business identity as
a parameter (ADR-0013). Resources belonging to another tenant answer 404 rather
than 403, so a foreign id is indistinguishable from a missing one.

Run with:  uvicorn marketing_os.entrypoints.api.app:app --reload
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel

from marketing_os.adapters.auth import JwksTokenVerifier
from marketing_os.adapters.deliverables import (
    FilesystemDeliverableStore,
    human_revisions_used,
)
from marketing_os.adapters.documents import FilesystemDocumentStore
from marketing_os.adapters.observability import (
    configure_logging,
    configure_tracing,
    get_logger,
    list_run_ids,
    new_run_id,
    read_events,
    tail_trace,
)
from marketing_os.adapters.questionnaire import InMemoryAnswerStore, InMemoryQuestionnaireStore
from marketing_os.adapters.runs import AWAITING_APPROVAL, CANCELLED, RUNNING, InMemoryRunStore
from marketing_os.adapters.tenants import PassthroughTenantDirectory
from marketing_os.config import Settings, load_settings
from marketing_os.entrypoints.env import load_env
from marketing_os.errors import (
    ConfigError,
    DocumentNotFoundError,
    GateError,
    MarketingOSError,
    RevisionLimitError,
    RunConflictError,
    StageNotAwaitingApprovalError,
    UnauthenticatedError,
    ValidationError,
)
from marketing_os.governance import check_gate
from marketing_os.governance.pipeline import PIPELINE, Stage, apply_approval_policies
from marketing_os.graph.registry import RunRegistry, read_run_status, resolve_trace_path
from marketing_os.graph.runner import arun_campaign, awaiting_approval_stage
from marketing_os.ports import (
    AnswerStore,
    DeliverableStore,
    DocumentStore,
    QuestionnaireStore,
    RunStore,
    TenantDirectory,
    TokenVerifier,
)
from marketing_os.questionnaire import completeness, render_brand_dna
from marketing_os.schemas import (
    ApprovalDecision,
    BrandDnaRecord,
    CampaignResult,
    DeliverableVersion,
    DnaAnswer,
    DnaCompleteness,
    Questionnaire,
    VerifiedIdentity,
)

if TYPE_CHECKING:
    from marketing_os.adapters.postgres import PostgresBackend

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
    if backend is not None:
        await backend.open()

    registry = get_registry()
    _LOGGER.info("service.started postgres=%s", backend is not None)
    reclaimed = await registry.reclaim_abandoned()
    if reclaimed:
        _LOGGER.info("service.reclaimed runs=%d", len(reclaimed))
    try:
        yield
    finally:
        if backend is not None:
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


@lru_cache(maxsize=1)
def get_backend() -> PostgresBackend | None:
    """Return the Postgres backend, or ``None`` when no DSN is configured.

    The single place the storage choice is made. Every other provider asks this
    one what it got, so "are we on Postgres?" is answered once rather than read
    from a mutable module global. The lifespan opens and closes it.

    Returns:
        The backend, or ``None`` to run on the filesystem and in memory.
    """
    dsn = get_settings().postgres_dsn
    if not dsn:
        return None
    from marketing_os.adapters.postgres import PostgresBackend

    return PostgresBackend(dsn)


@lru_cache(maxsize=1)
def get_document_store() -> DocumentStore:
    """Return the process-wide document store tenant documents resolve through.

    Returns:
        The Postgres adapter when a DSN is configured, otherwise the filesystem
        adapter rooted at the repo root (tests reset it with
        ``get_document_store.cache_clear()``, mirroring settings).
    """
    backend = get_backend()
    if backend is not None:
        return backend.documents
    return FilesystemDocumentStore(get_settings().root)


@lru_cache(maxsize=1)
def get_deliverable_store() -> DeliverableStore:
    """Return the process-wide store holding each deliverable's version history.

    Returns:
        The Postgres adapter when a DSN is configured — where a halted run's
        history survives a restart — otherwise the filesystem adapter rooted at
        the repo root.
    """
    backend = get_backend()
    if backend is not None:
        return backend.deliverables
    return FilesystemDeliverableStore(get_settings().root)


@lru_cache(maxsize=1)
def get_tenant_directory() -> TenantDirectory:
    """Return the process-wide directory mapping IdP organizations to tenants.

    Returns:
        The Postgres directory when a DSN is configured — which mints a platform
        ``tenant_id`` and keeps the IdP's organization id in its own column —
        otherwise the passthrough directory, which reports the organization id
        as the tenant id because a filesystem tenant *is* a directory name
        (ADR-0014).
    """
    backend = get_backend()
    if backend is not None:
        return backend.tenants
    return PassthroughTenantDirectory()


@lru_cache(maxsize=1)
def get_checkpointer() -> BaseCheckpointSaver:
    """Return the process-wide checkpointer runs are resumable through.

    A single instance for the process — not one per run — is what makes a
    checkpoint outlive the run that wrote it, and therefore what makes
    abandoning a cancelled run's threads a real operation rather than a no-op.

    Returns:
        The Postgres saver when a DSN is configured, otherwise a process-wide
        :class:`MemorySaver`, which survives runs but not a restart.
    """
    backend = get_backend()
    if backend is not None:
        return backend.checkpointer
    return MemorySaver()


@lru_cache(maxsize=1)
def get_run_store() -> RunStore:
    """Return the process-wide store holding run claims and statuses.

    Returns:
        The Postgres store when a DSN is configured — shared by every worker —
        otherwise an in-process store, which limits the service to one worker.
    """
    backend = get_backend()
    if backend is not None:
        return backend.runs
    return InMemoryRunStore()


@lru_cache(maxsize=1)
def get_questionnaire_store() -> QuestionnaireStore:
    """Return the process-wide store holding the published question set.

    Returns:
        The Postgres store when a DSN is configured — where an admin publishes a
        new version without a deploy — otherwise an in-process store, which
        serves the code-shipped seed set.
    """
    backend = get_backend()
    if backend is not None:
        return backend.questionnaires
    return InMemoryQuestionnaireStore()


@lru_cache(maxsize=1)
def get_answer_store() -> AnswerStore:
    """Return the process-wide store holding each business's Brand DNA answers.

    Returns:
        The Postgres store when a DSN is configured, otherwise an in-process
        store, which loses answers on restart and is for local work only.
    """
    backend = get_backend()
    if backend is not None:
        return backend.answers
    return InMemoryAnswerStore()


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
    caller learns "sign in", not "the server is broken".

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
        raise _http_error(UnauthenticatedError("Sign in to continue."))
    try:
        claims = get_token_verifier().verify(token.strip())
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
    get_registry,
)


def reset_providers() -> None:
    """Drop every cached provider so the next call rebuilds it.

    Called when the service shuts down, and by tests between cases, since every
    provider's answer depends on the settings and the storage backend.
    """
    for provider in _BACKED_PROVIDERS:
        provider.cache_clear()


class DnaAnswersUpsert(BaseModel):
    """Request body for saving Brand DNA answers.

    Upsert rather than replace, so the wizard can save partway and resume, and a
    single answer can be edited later without resending the rest.

    Attributes:
        answers: The answers to save; at least one.
    """

    answers: list[DnaAnswer]


class CreateCampaign(BaseModel):
    """Request body for scaffolding a campaign.

    Carries no business identity: the tenant comes from the verified token
    (ADR-0013), so this body describes only the campaign itself.

    Attributes:
        slug: The campaign slug.
    """

    slug: str


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
        The user id, email, and business name from the verified claim.
    """
    return {
        "user_id": identity.user_id,
        "email": identity.email,
        "business_name": identity.business_name or identity.tenant_id,
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
        markdown projection, and the structured answers behind it.
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


@app.post("/campaigns")
def create_campaign(body: CreateCampaign, identity: Identity) -> dict[str, object]:
    """Scaffold a campaign goal from the template and report the gate.

    Args:
        body: The create-campaign request.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The slug, whether the goal was created, and the gate status.

    Raises:
        HTTPException: If the campaign-goal template is missing.
    """
    settings = get_settings()
    store = get_document_store()
    tenant = identity.tenant_id
    slug = body.slug
    goal_document = f"campaigns/{slug}/goal.md"
    created = False
    if not store.exists(tenant, goal_document):
        template = settings.templates_dir / "campaign-goal.md"
        if not template.is_file():
            raise HTTPException(500, "campaign-goal template missing")
        store.write(tenant, goal_document, template.read_text(encoding="utf-8"))
        created = True
    report = check_gate(
        settings, tenant, slug, store=store, questionnaire=get_questionnaire_store().published()
    )
    return {
        "slug": slug,
        "goal_created_from_template": created,
        "gate_ok": report.ok,
        "gate_issues": report.all_issues,
    }


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
        The campaign slug and the list of written documents.

    Raises:
        HTTPException: 404 if the caller's tenant has no such campaign.
    """
    store = get_document_store()
    documents = store.list(identity.tenant_id, f"campaigns/{slug}")
    if not documents:
        raise _http_error(DocumentNotFoundError(f"No campaign '{slug}'"))
    files = [
        {"name": document.rsplit("/", 1)[-1], "path": document}
        for document in documents
        if document.endswith(".md")
    ]
    return {"slug": slug, "files": files}


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
    store = get_document_store()
    if not name.endswith(".md") or not store.exists(identity.tenant_id, document):
        raise _http_error(DocumentNotFoundError(f"No deliverable '{name}' for campaign '{slug}'"))
    return {
        "name": name,
        "path": document,
        "content": store.read(identity.tenant_id, document),
    }


@app.get("/campaigns/{slug}/stages")
async def stages(slug: str, identity: Identity) -> dict[str, object]:
    """Report each pipeline stage with its approval policy and where it has got to.

    The approval policy is reported alongside the stage so the interface can say
    which stages the system handles itself and which will stop and ask — before
    the run starts, not when it halts (ADR-0015).

    Args:
        slug: The campaign slug.
        identity: The verified identity whose tenant owns the campaign.

    Returns:
        The campaign slug and its stages in mandatory pipeline order, each with
        its key, operator Phase, state, approval policy, and latest deliverable
        version if it has one.
    """
    tenant = identity.tenant_id
    versions = get_deliverable_store()
    configured = apply_approval_policies(PIPELINE, get_settings().human_gate_stages)
    waiting = await _stage_awaiting_approval(tenant, slug)
    reported = [
        _report_stage(stage, versions.latest(tenant, slug, stage.key), waiting)
        for stage in configured
    ]
    return {"slug": slug, "stages": reported}


async def _stage_awaiting_approval(tenant: str, slug: str) -> str | None:
    """Return the stage a campaign's live run is halted at, if one is.

    Read from the checkpoint, the same durable source the approve and revise
    endpoints consult, so the stepper cannot disagree with what those endpoints
    will accept — and so the answer holds when run tracing is switched off.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        The waiting stage key, or ``None`` when no run is holding at a gate.
    """
    record = get_registry().active_for_campaign(tenant, slug)
    if record is None or record.status != AWAITING_APPROVAL:
        return None
    return await awaiting_approval_stage(
        tenant, slug, stage=record.stage, checkpointer=get_checkpointer()
    )


def _report_stage(
    stage: Stage, latest: DeliverableVersion | None, waiting: str | None
) -> dict[str, object]:
    """Describe one stage for the interface: its phase, its state, and its policy.

    The phase is what the operator's stepper groups by, so the interface renders
    its designed steps without the engine adopting UI vocabulary (ADR-0017).

    Args:
        stage: The pipeline stage, carrying its configured approval policy.
        latest: The newest version of its deliverable, if it has produced one.
        waiting: The stage currently halted at an Approval Gate, if any.

    Returns:
        The stage's key, phase, state, approval policy, and latest version.
    """
    if stage.key == waiting:
        state = AWAITING_APPROVAL
    elif latest is not None:
        state = "completed"
    else:
        state = "pending"
    return {
        "key": stage.key,
        "phase": stage.phase,
        "state": state,
        "approval_policy": stage.approval_policy,
        "latest_version": latest.version if latest else None,
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
        HTTPException: 409 if the gate failed or the slug already has an active run.
    """
    settings = get_settings()
    store = get_document_store()
    tenant = identity.tenant_id
    report = check_gate(
        settings, tenant, slug, store=store, questionnaire=get_questionnaire_store().published()
    )
    if not report.ok:
        raise _http_error(GateError("Stage 0 gate failed", missing=report.all_issues))
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
    settings = get_settings()
    registry = get_registry()
    record = registry.get(run_id, identity.tenant_id)
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    tenant = record.tenant_id
    slug = record.slug
    waiting = await awaiting_approval_stage(
        tenant, slug, stage=record.stage, checkpointer=get_checkpointer()
    )
    if waiting != decision.stage_key:
        raise _http_error(StageNotAwaitingApprovalError(decision.stage_key))
    if record.status != AWAITING_APPROVAL:
        _LOGGER.warning(
            "run.gate_out_of_sync run_id=%s slug=%s recorded=%s checkpoint_stage=%s",
            run_id,
            slug,
            record.status,
            waiting,
        )
        if registry.mark_awaiting_approval(run_id, tenant) is None:
            raise _http_error(StageNotAwaitingApprovalError(decision.stage_key))

    async def relaunch() -> CampaignResult:
        """Continue the halted run from its Approval Gate.

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
            resume=Command(resume=decision.model_dump()),
        )

    resumed = registry.resume(
        run_id=run_id, tenant=tenant, user_id=identity.user_id, launch=relaunch
    )
    if resumed is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    return {"run_id": run_id, "slug": slug, "stage": decision.stage_key, "status": RUNNING}


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
        HTTPException: 404 if the caller has no such run; 409 if the named stage
            is not awaiting approval, or its revision cap is spent; 422 if the
            feedback is empty — a refusal with nothing to act on would re-run
            the stage identically and charge for it.
    """
    feedback = body.feedback.strip()
    if not feedback:
        raise _http_error(ValidationError("Say what you want changed."))
    record = get_registry().get(run_id, identity.tenant_id)
    if record is None:
        raise _http_error(DocumentNotFoundError(f"No run '{run_id}'"))
    _refuse_when_revisions_spent(identity.tenant_id, record.slug, body.stage_key)
    decision = ApprovalDecision(stage_key=body.stage_key, approved=False, feedback=feedback)
    return await _resume_run(run_id, identity, decision)


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
    ``run.summary`` event, at which point the stream closes. Because it only reads the
    durable trace, any number of observers can attach to the same run concurrently,
    and a finished run replays and closes.

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
