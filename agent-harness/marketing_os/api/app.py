"""FastAPI service exposing the harness over HTTP.

Endpoints:
  GET  /health
  POST /campaigns                       -> scaffold a campaign goal from the template
  GET  /campaigns/{slug}/gate?customer= -> Stage 0 gate report
  GET  /campaigns/{slug}/deliverables   -> list written deliverables
  POST /campaigns/{slug}/run            -> run the pipeline (or one stage), return results
  GET  /campaigns/{slug}/stream?customer=&stage= -> SSE progress stream

Run with:  uvicorn marketing_os.api.app:app --reload
"""

from __future__ import annotations

import json
import queue
import shutil
import threading
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import Settings, load_settings
from ..errors import GateError, MarketingOSError
from ..governance import check_gate
from ..types import ReviewVerdict, StageResult

app = FastAPI(title="Marketing OS", version="0.1.0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


# ── Serialization helpers ─────────────────────────────────────────────────────
def _verdict_dict(v: Optional[ReviewVerdict]) -> Optional[dict]:
    if v is None:
        return None
    return {
        "passed": v.passed,
        "summary": v.summary,
        "discrepancies": [
            {"rubric_point": d.rubric_point, "problem": d.problem, "fix": d.fix}
            for d in v.discrepancies
        ],
    }


def _stage_dict(s: StageResult) -> dict:
    return {
        "stage": s.stage,
        "deliverable_path": s.deliverable_path,
        "qa_iterations": s.qa_iterations,
        "approved": s.approved,
        "verdict": _verdict_dict(s.verdict),
        "usage": {"input_tokens": s.usage.input_tokens, "output_tokens": s.usage.output_tokens},
    }


# ── Request models ──────────────────────────────────────────────────────────
class CreateCampaign(BaseModel):
    customer: str
    slug: Optional[str] = None


class RunCampaign(BaseModel):
    customer: str
    stage: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "provider": s.provider, "root": str(s.root)}


@app.post("/campaigns")
def create_campaign(body: CreateCampaign) -> dict:
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
    s = get_settings()
    report = check_gate(s, customer, slug)
    return {"ok": report.ok, "issues": report.all_issues}


@app.get("/campaigns/{slug}/deliverables")
def deliverables(slug: str) -> dict:
    s = get_settings()
    cdir = s.campaigns_dir / slug
    if not cdir.is_dir():
        raise HTTPException(404, f"No campaign '{slug}'")
    files = [
        {"name": f.name, "size_bytes": f.stat().st_size}
        for f in sorted(cdir.glob("*.md"))
    ]
    return {"slug": slug, "files": files}


@app.post("/campaigns/{slug}/run")
def run(slug: str, body: RunCampaign) -> dict:
    s = get_settings()
    from ..orchestrator import MarketingDirector

    try:
        director = MarketingDirector(s, hooks=None)
        result = director.run_campaign(body.customer, slug, only_stage=body.stage)
    except GateError as exc:
        raise HTTPException(409, str(exc)) from exc
    except MarketingOSError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "slug": result.slug,
        "customer": result.customer,
        "stages": [_stage_dict(st) for st in result.stages],
        "usage": {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
        },
    }


@app.get("/campaigns/{slug}/stream")
def stream(slug: str, customer: str, stage: Optional[str] = None) -> StreamingResponse:
    s = get_settings()
    from ..orchestrator import MarketingDirector

    q: "queue.Queue[Optional[dict]]" = queue.Queue()

    def worker() -> None:
        director = MarketingDirector(s, hooks=None, on_event=lambda e: q.put(e))
        try:
            result = director.run_campaign(customer, slug, only_stage=stage)
            q.put({"event": "campaign.done", "stages": [_stage_dict(st) for st in result.stages]})
        except Exception as exc:  # noqa: BLE001 - report any failure to the client
            q.put({"event": "error", "message": str(exc)})
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
