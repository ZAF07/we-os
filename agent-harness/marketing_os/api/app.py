"""FastAPI service exposing the harness over HTTP, with human-approval resume.

Endpoints:
  GET  /health
  POST /campaigns                         scaffold campaigns/<slug>/goal.md from template
  GET  /campaigns/{slug}/gate?customer=    Stage-0 gate report
  GET  /campaigns/{slug}/deliverables      list written deliverable files
  POST /campaigns/{slug}/run               start a run (background); returns run_id
  GET  /runs/{run_id}                       run status + result + pending approvals
  GET  /runs/{run_id}/stream                SSE progress stream
  POST /approvals/{approval_id}             resolve a pending human-approval gate

Runs execute as background asyncio tasks in this process. A run that hits the
human-approval tool registers a pending approval and awaits it; `POST
/approvals/{id}` fulfills it and the run resumes. (Single-process; for multi-worker
deployments back the run/approval registry with shared storage.)
"""

from __future__ import annotations

import asyncio
import shutil
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import Settings, load_settings
from ..errors import MarketingOSError
from ..governance import check_gate

app = FastAPI(title="Marketing OS (ADK)", version="0.2.0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


# ── In-process run + approval registry ────────────────────────────────────────
@dataclass
class RunState:
    """Tracks one background campaign run."""

    run_id: str
    customer: str
    slug: str
    status: str = "running"  # running | paused | done | error
    events: list = field(default_factory=list)
    pending: dict = field(default_factory=dict)  # approval_id -> {"payload", "future"}
    result: Optional[dict] = None
    error: Optional[str] = None
    queue: "asyncio.Queue" = field(default_factory=asyncio.Queue)


_RUNS: dict[str, RunState] = {}


# ── Request models ────────────────────────────────────────────────────────────
class CreateCampaign(BaseModel):
    customer: str
    slug: Optional[str] = None


class RunCampaign(BaseModel):
    customer: str
    provider: Optional[str] = None
    fresh: bool = False  # ignore any checkpoint and start over (default: resume)


class ApprovalDecision(BaseModel):
    status: str  # "approved" | "rejected"
    comment: str = ""


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "provider": s.provider, "root": str(s.root)}


@app.post("/campaigns")
def create_campaign(body: CreateCampaign) -> dict:
    """Scaffold campaigns/<slug>/goal.md from the template; report the gate."""
    s = get_settings()
    slug = body.slug or body.customer
    cdir = s.campaigns_dir / slug
    cdir.mkdir(parents=True, exist_ok=True)
    goal = cdir / "goal.md"
    created = False
    if not goal.is_file():
        template = s.templates_dir / "campaign-goal.md"
        if not template.is_file():
            raise HTTPException(500, "campaign-goal template missing")
        shutil.copy(template, goal)
        created = True
    report = check_gate(s, body.customer, slug)
    return {
        "slug": slug,
        "customer": body.customer,
        "goal_created_from_template": created,
        "gate_ok": report.ok,
        "gate_issues": report.all_issues,
    }


@app.get("/campaigns/{slug}/gate")
def gate(slug: str, customer: str) -> dict:
    """Run the Stage-0 gate and return its report."""
    report = check_gate(get_settings(), customer, slug)
    return {"ok": report.ok, "issues": report.all_issues}


@app.get("/campaigns/{slug}/runstate")
def runstate(slug: str) -> dict:
    """Inspect a campaign's saved checkpoint (which stages are already complete)."""
    from ..runstate import completed_stages, load_checkpoint

    cp = load_checkpoint(get_settings(), slug)
    if cp is None:
        return {"slug": slug, "checkpoint": False, "completed": []}
    return {"slug": slug, "checkpoint": True, "completed": completed_stages(cp)}


@app.get("/campaigns/{slug}/deliverables")
def deliverables(slug: str) -> dict:
    """List the markdown deliverables written for a campaign."""
    cdir = get_settings().campaigns_dir / slug
    if not cdir.is_dir():
        raise HTTPException(404, f"no campaign '{slug}'")
    files = [{"name": f.name, "size_bytes": f.stat().st_size} for f in sorted(cdir.glob("*.md"))]
    return {"slug": slug, "files": files}


@app.post("/campaigns/{slug}/run")
async def run(slug: str, body: RunCampaign) -> dict:
    """Start a campaign run in the background; return its run_id immediately."""
    s = get_settings()
    report = check_gate(s, body.customer, slug)
    if not report.ok:
        raise HTTPException(409, {"message": "gate failed", "issues": report.all_issues})

    run_id = uuid.uuid4().hex
    state = RunState(run_id=run_id, customer=body.customer, slug=slug)
    _RUNS[run_id] = state
    asyncio.create_task(_run_campaign(state, body.provider, body.fresh))
    return {"run_id": run_id, "status": state.status}


@app.get("/runs/{run_id}")
def run_status(run_id: str) -> dict:
    """Return a run's status, result, and any pending approvals."""
    state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(404, "unknown run")
    return {
        "run_id": run_id,
        "status": state.status,
        "result": state.result,
        "error": state.error,
        "pending_approvals": [
            {"approval_id": aid, "payload": rec["payload"]} for aid, rec in state.pending.items()
        ],
    }


@app.get("/runs/{run_id}/stream")
async def run_stream(run_id: str) -> StreamingResponse:
    """Stream a run's progress events as Server-Sent Events."""
    state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(404, "unknown run")

    import json

    async def gen():
        # Replay buffered events, then tail the live queue.
        for e in list(state.events):
            yield f"data: {json.dumps(e)}\n\n"
        while state.status in ("running", "paused"):
            try:
                e = await asyncio.wait_for(state.queue.get(), timeout=15.0)
                yield f"data: {json.dumps(e)}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
        yield f"data: {json.dumps({'event': 'closed', 'status': state.status})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/approvals/{approval_id}")
def resolve_approval(approval_id: str, decision: ApprovalDecision) -> dict:
    """Resolve a pending human-approval gate, resuming the paused run."""
    for state in _RUNS.values():
        rec = state.pending.get(approval_id)
        if rec is not None:
            if not rec["future"].done():
                rec["future"].set_result(decision.model_dump())
            return {"approval_id": approval_id, "accepted": True}
    raise HTTPException(404, "unknown or already-resolved approval")


# ── Background run driver ─────────────────────────────────────────────────────
async def _run_campaign(state: RunState, provider: Optional[str], fresh: bool = False) -> None:
    """Execute a campaign run, wiring events and the approval gate into the registry."""
    from ..orchestrator import MarketingDirector

    def on_event(e: dict) -> None:
        state.events.append(e)
        state.queue.put_nowait(e)

    async def approval_handler(payload: dict) -> dict:
        """Register a pending approval and await the API resume call."""
        approval_id = uuid.uuid4().hex
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        state.pending[approval_id] = {"payload": payload, "future": future}
        state.status = "paused"
        on_event({"event": "approval.pending", "approval_id": approval_id, **payload})
        decision = await future
        state.pending.pop(approval_id, None)
        state.status = "running"
        return decision

    director = MarketingDirector(
        get_settings(), provider=provider, on_event=on_event, approval_handler=approval_handler
    )
    try:
        result = await director.run_campaign(state.customer, state.slug, fresh=fresh)
        state.result = {
            "deliverables": result.deliverables,
            "violations": result.violations,
            "steps": len(result.steps),
        }
        state.status = "done"
    except MarketingOSError as exc:
        state.error = str(exc)
        state.status = "error"
    except Exception as exc:  # noqa: BLE001 - surface any run failure to the client
        state.error = f"{type(exc).__name__}: {exc}"
        state.status = "error"
