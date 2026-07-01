"""FastAPI service exposing the Marketing OS graph over HTTP.

Endpoints:
  GET  /health
  POST /campaigns                       -> scaffold a campaign goal from the template
  GET  /campaigns/{slug}/gate?customer= -> Stage 0 gate report
  GET  /campaigns/{slug}/deliverables   -> list written deliverables
  POST /campaigns/{slug}/run            -> run the pipeline (or one stage), return results
  GET  /campaigns/{slug}/stream?customer=&stage= -> SSE progress stream

Run with:  uvicorn marketing_os.entrypoints.api.app:app --reload
"""

from __future__ import annotations

import json
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from marketing_os.adapters.observability import configure_logging, configure_tracing
from marketing_os.config import Settings, load_settings
from marketing_os.errors import GateError, MarketingOSError
from marketing_os.governance import check_gate
from marketing_os.graph.runner import astream_campaign, run_campaign


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Configure logging and LangSmith tracing for the service lifetime.

    Args:
        _: The FastAPI application (unused).

    Yields:
        Control for the duration of the application's lifespan.
    """
    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    yield


app = FastAPI(title="Marketing OS", version="0.2.0", lifespan=_lifespan)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached harness settings.

    Returns:
        The process-wide :class:`Settings` instance.
    """
    return load_settings()


class CreateCampaign(BaseModel):
    """Request body for scaffolding a campaign.

    Attributes:
        customer: The customer name.
        slug: The campaign slug; defaults to the customer name.
    """

    customer: str
    slug: str | None = None


class RunCampaign(BaseModel):
    """Request body for running a campaign.

    Attributes:
        customer: The customer name.
        stage: The single stage to run, or ``None`` for the full pipeline.
    """

    customer: str
    stage: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Report service health and the active provider and root.

    Returns:
        A status payload.
    """
    settings = get_settings()
    return {"status": "ok", "provider": settings.provider, "root": str(settings.root)}


@app.post("/campaigns")
def create_campaign(body: CreateCampaign) -> dict[str, object]:
    """Scaffold a campaign goal from the template and report the gate.

    Args:
        body: The create-campaign request.

    Returns:
        The slug, whether the goal was created, and the gate status.

    Raises:
        HTTPException: If the campaign-goal template is missing.
    """
    settings = get_settings()
    slug = body.slug or body.customer
    campaign_dir = settings.campaigns_dir / slug
    campaign_dir.mkdir(parents=True, exist_ok=True)
    goal = campaign_dir / "goal.md"
    created = False
    if not goal.is_file():
        template = settings.templates_dir / "campaign-goal.md"
        if not template.is_file():
            raise HTTPException(500, "campaign-goal template missing")
        shutil.copy(template, goal)
        created = True
    report = check_gate(settings, body.customer, slug)
    return {
        "slug": slug,
        "customer": body.customer,
        "goal_created_from_template": created,
        "gate_ok": report.ok,
        "gate_issues": report.all_issues,
    }


@app.get("/campaigns/{slug}/gate")
def gate(slug: str, customer: str) -> dict[str, object]:
    """Return the Stage 0 gate report for a campaign.

    Args:
        slug: The campaign slug.
        customer: The customer name.

    Returns:
        The gate status and any issues.
    """
    settings = get_settings()
    report = check_gate(settings, customer, slug)
    return {"ok": report.ok, "issues": report.all_issues}


@app.get("/campaigns/{slug}/deliverables")
def deliverables(slug: str) -> dict[str, object]:
    """List the deliverable files written for a campaign.

    Args:
        slug: The campaign slug.

    Returns:
        The campaign slug and the list of written files.

    Raises:
        HTTPException: If the campaign directory does not exist.
    """
    settings = get_settings()
    campaign_dir = settings.campaigns_dir / slug
    if not campaign_dir.is_dir():
        raise HTTPException(404, f"No campaign '{slug}'")
    files = [
        {"name": f.name, "size_bytes": f.stat().st_size} for f in sorted(campaign_dir.glob("*.md"))
    ]
    return {"slug": slug, "files": files}


@app.post("/campaigns/{slug}/run")
def run(slug: str, body: RunCampaign) -> dict[str, object]:
    """Run the pipeline (or one stage) and return the structured result.

    Args:
        slug: The campaign slug.
        body: The run request.

    Returns:
        The campaign result payload.

    Raises:
        HTTPException: 409 if the gate failed, 422 for any other harness error.
    """
    settings = get_settings()
    try:
        result = run_campaign(settings, body.customer, slug, stage=body.stage)
    except GateError as exc:
        raise HTTPException(409, _error_detail(exc)) from exc
    except MarketingOSError as exc:
        raise HTTPException(422, _error_detail(exc)) from exc
    return result.model_dump()


def _error_detail(exc: MarketingOSError) -> dict[str, object]:
    """Build the structured error body for a failed run.

    Args:
        exc: The raised harness error, which may carry a ``detail`` payload with
            the stage, discrepancies, and run-log path.

    Returns:
        The structured detail dict returned to the client.
    """
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        return detail
    return {"message": str(exc)}


@app.get("/campaigns/{slug}/runs")
def list_runs(slug: str) -> dict[str, object]:
    """List the run-log traces recorded for a campaign.

    Args:
        slug: The campaign slug.

    Returns:
        The campaign slug and the available run ids (newest first).
    """
    settings = get_settings()
    runs_dir = settings.logs_dir / slug
    if not runs_dir.is_dir():
        return {"slug": slug, "runs": []}
    runs = sorted((f.stem for f in runs_dir.glob("*.jsonl")), reverse=True)
    return {"slug": slug, "runs": runs}


@app.get("/campaigns/{slug}/runs/{run_id}")
def get_run(slug: str, run_id: str) -> dict[str, object]:
    """Return the parsed JSONL trace for one run.

    Args:
        slug: The campaign slug.
        run_id: The run id (trace filename without extension).

    Returns:
        The campaign slug, run id, and the list of trace events.

    Raises:
        HTTPException: 404 if the trace does not exist.
    """
    settings = get_settings()
    path = settings.logs_dir / slug / f"{run_id}.jsonl"
    if not path.is_file():
        raise HTTPException(404, f"No run '{run_id}' for campaign '{slug}'")
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {"slug": slug, "run_id": run_id, "events": events}


@app.get("/campaigns/{slug}/stream")
def stream(slug: str, customer: str, stage: str | None = None) -> StreamingResponse:
    """Stream campaign progress as Server-Sent Events.

    Args:
        slug: The campaign slug.
        customer: The customer name.
        stage: The single stage to run, or ``None`` for the full pipeline.

    Returns:
        A streaming response emitting one SSE ``data:`` line per progress event.
    """
    settings = get_settings()

    async def event_source() -> AsyncIterator[str]:
        """Yield each progress event as an SSE ``data:`` frame.

        Yields:
            SSE-formatted event lines.
        """
        async for event in astream_campaign(settings, customer, slug, stage=stage):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
