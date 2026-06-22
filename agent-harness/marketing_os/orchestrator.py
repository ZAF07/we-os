"""The Marketing Director — drives a campaign run on ADK.

Responsibilities:
- enforce the Stage-0 Customer DNA gate before any model call;
- build the per-run tools (filesystem + a fresh browser), model, and coordinator;
- run the coordinator via an ADK `Runner`, seeding session state with the overall
  goal and the Customer DNA so every agent can self-check against them;
- handle the human-approval pause/resume loop (long-running approval tool);
- persist the finished session to long-term memory for future-task retrieval.

`run_campaign` is async (ADK's runtime is async); `run_campaign_sync` wraps it.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import errors as genai_errors
from google.genai import types

from .agents import BuildContext, load_registry
from .config import Settings, supports_structured_output
from .governance import enforce_gate, load_governance
from .memory import FileBackedMemoryService
from .model import build_model
from .pipeline import DELIVERABLE_KEYS, build_coordinator
from .runstate import clear_checkpoint, completed_stages, load_checkpoint, save_checkpoint
from .tools import FilesystemTools, WebBrowser
from .tools.approval import APPROVAL_TOOL_NAME

# HTTP-ish codes that are worth a transient retry / resume (overload, rate limit,
# gateway hiccups) — e.g. Gemini's 503 "high demand".
_TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}


def _is_transient(exc: BaseException) -> bool:
    """True if `exc` is a retryable model/transport error (overload, rate limit)."""
    if isinstance(exc, genai_errors.ServerError):  # all 5xx
        return True
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return isinstance(exc, genai_errors.APIError) and code in _TRANSIENT_CODES

# Approval handler: given the approval payload, return the human's decision dict
# (e.g. {"status": "approved"} | {"status": "rejected", "comment": "..."}).
# May be sync or async; may block (the run waits on it).
ApprovalHandler = Callable[[dict], "dict | Awaitable[dict]"]
EventSink = Callable[[dict], None]


@dataclass
class CampaignResult:
    """Outcome of a campaign run."""

    customer: str
    slug: str
    deliverables: dict = field(default_factory=dict)  # stage key -> structured JSON
    steps: list = field(default_factory=list)  # captured DecisionEnvelope trace
    violations: list = field(default_factory=list)
    notes: list = field(default_factory=list)


class MarketingDirector:
    """Builds and runs the ADK coordinator for one customer/campaign."""

    def __init__(
        self,
        settings: Settings,
        *,
        provider: Optional[str] = None,
        on_event: Optional[EventSink] = None,
        approval_handler: Optional[ApprovalHandler] = None,
        headless: bool = True,
        max_transient_retries: int = 3,
        transient_backoff: float = 10.0,
    ) -> None:
        """Wire the director.

        Args:
            settings: Resolved settings.
            provider: Optional provider override (else the active one).
            on_event: Optional sink for progress events (CLI prints / SSE).
            approval_handler: Optional human-approval resolver; if omitted, approval
                requests auto-approve with a note (so library/test runs don't hang).
            headless: Run the browser headless.
            max_transient_retries: How many times to auto-retry a transient model
                error (e.g. a 503) before giving up; the run resumes where it stopped.
            transient_backoff: Base seconds for exponential backoff between retries.
        """
        self.settings = settings
        self.provider = provider
        self.on_event = on_event
        self.approval_handler = approval_handler
        self.headless = headless
        self.max_transient_retries = max_transient_retries
        self.transient_backoff = transient_backoff

    # ── Public API ────────────────────────────────────────────────────────────
    async def run_campaign(
        self,
        customer: str,
        slug: Optional[str] = None,
        *,
        resume: bool = True,
        fresh: bool = False,
    ) -> CampaignResult:
        """Run (or resume) the full pipeline for a customer/campaign.

        State is checkpointed to `campaigns/<slug>/.run_state.json` after each
        stage. By default a run **resumes** from that checkpoint — completed stages
        are skipped and work continues where it stopped (after a crash or a
        transient model error). Transient errors are auto-retried in-process.

        Args:
            customer: Customer folder name under `customers/`.
            slug: Campaign slug under `campaigns/` (defaults to the customer name).
            resume: Pre-seed state from an existing checkpoint and skip done stages.
            fresh: Ignore/clear any checkpoint and start over (overrides `resume`).

        Returns:
            A CampaignResult with the structured deliverables and the step trace.

        Raises:
            GateError: if the Stage-0 gate fails.
        """
        slug = slug or customer
        self._emit({"event": "gate.start", "customer": customer, "slug": slug})
        enforce_gate(self.settings, customer, slug)
        self._emit({"event": "gate.passed", "customer": customer, "slug": slug})

        dna = (self.settings.customers_dir / customer / "dna.md").read_text(encoding="utf-8")
        goal = (self.settings.campaigns_dir / slug / "goal.md").read_text(encoding="utf-8")
        (self.settings.campaigns_dir / slug).mkdir(parents=True, exist_ok=True)

        # Seed = fresh governance context + (on resume) the prior run's deliverables.
        if fresh:
            clear_checkpoint(self.settings, slug)
        checkpoint = None if fresh else (load_checkpoint(self.settings, slug) if resume else None)
        seed: dict = dict(checkpoint or {})
        seed.update(  # always refresh governance inputs from disk
            {"overall_goal": goal.strip(), "dna": dna, "goal": goal, "slug": slug, "customer": customer}
        )
        if checkpoint:
            done = completed_stages(seed)
            self._emit({"event": "resume", "slug": slug, "completed": done})

        browser = WebBrowser(headless=self.headless)
        ctx = BuildContext(
            settings=self.settings,
            model=build_model(self.settings, self.provider),
            governance=load_governance(self.settings),
            registry=load_registry(self.settings),
            fs=FilesystemTools(self.settings.root),
            browser=browser,
            on_step=lambda rec: self._emit({"event": "step", **rec}),
            structured_output=supports_structured_output(self.provider or self.settings.provider),
        )
        coordinator = build_coordinator(ctx)

        session_service = InMemorySessionService()
        memory_service = FileBackedMemoryService(self.settings.memory_db)
        runner = Runner(
            app_name=self.settings.app_name,
            agent=coordinator,
            session_service=session_service,
            memory_service=memory_service,
        )
        user_id = f"customer:{customer}"
        session = await session_service.create_session(
            app_name=self.settings.app_name, user_id=user_id, state=seed
        )

        # Live accumulator: starts from the seed, updated from each event's
        # state_delta, and checkpointed after every stage so a crash loses nothing.
        acc: dict = dict(seed)
        try:
            await self._drive(runner, user_id, session.id, slug, acc)
            session = await session_service.get_session(
                app_name=self.settings.app_name, user_id=user_id, session_id=session.id
            )
            await memory_service.add_session_to_memory(session)
            acc.update(dict(session.state or {}))
        finally:
            save_checkpoint(self.settings, slug, acc)  # persist even on failure
            await browser.close()

        result = CampaignResult(
            customer=customer,
            slug=slug,
            deliverables={k: acc[k] for k in DELIVERABLE_KEYS if k in acc},
            steps=acc.get("steps", []),
            violations=acc.get("violations", []),
            notes=acc.get("notes", []),
        )
        self._emit({"event": "campaign.done", "slug": slug, "stages": list(result.deliverables)})
        return result

    def run_campaign_sync(
        self, customer: str, slug: Optional[str] = None, *, resume: bool = True, fresh: bool = False
    ) -> CampaignResult:
        """Synchronous wrapper around `run_campaign` (for the CLI)."""
        return asyncio.run(self.run_campaign(customer, slug, resume=resume, fresh=fresh))

    # ── Run loop: transient-retry wrapper around the approval-aware drive ───────
    async def _drive(
        self, runner: Runner, user_id: str, session_id: str, slug: str, acc: dict
    ) -> None:
        """Drive the coordinator, auto-retrying transient model errors.

        Each retry re-enters the run on the SAME in-process session, whose state
        already holds the completed stages — so the resume skip-guards jump past
        them and only the failed stage re-runs. A non-transient error is re-raised
        after the partial state has been checkpointed by the caller's `finally`.
        """
        for attempt in range(self.max_transient_retries + 1):
            try:
                await self._drive_once(runner, user_id, session_id, slug, acc)
                return
            except BaseException as exc:  # noqa: BLE001 - classify, then re-raise non-transient
                if not _is_transient(exc) or attempt == self.max_transient_retries:
                    raise
                delay = self.transient_backoff * (2**attempt)
                self._emit(
                    {
                        "event": "transient_retry",
                        "slug": slug,
                        "attempt": attempt + 1,
                        "delay_s": delay,
                        "error": str(exc)[:200],
                    }
                )
                await asyncio.sleep(delay)

    async def _drive_once(
        self, runner: Runner, user_id: str, session_id: str, slug: str, acc: dict
    ) -> None:
        """Run the coordinator once, pausing/resuming for human-approval requests.

        ADK ends a turn when it hits an unfulfilled long-running tool call (our
        approval tool). We detect that pending call, resolve the human decision, and
        resume via a function response — looping until the run completes. Along the
        way we fold each event's `state_delta` into `acc` and checkpoint after every
        completed stage.
        """
        new_message: types.Content | None = types.Content(
            role="user",
            parts=[types.Part(text="Begin the campaign. Follow the pipeline stage by stage.")],
        )
        while True:
            pending = None
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=new_message
            ):
                self._emit_event(event)
                self._absorb_state(event, slug, acc)
                long_running = event.long_running_tool_ids or set()
                for fc in event.get_function_calls() or []:
                    if fc.name == APPROVAL_TOOL_NAME and fc.id in long_running:
                        pending = fc
            if pending is None:
                return
            decision = await self._resolve_approval(dict(pending.args or {}))
            new_message = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=pending.id, name=pending.name, response=decision
                        )
                    )
                ],
            )

    def _absorb_state(self, event: Any, slug: str, acc: dict) -> None:
        """Fold an event's state delta into `acc`; checkpoint when a stage finishes."""
        actions = getattr(event, "actions", None)
        delta = getattr(actions, "state_delta", None) if actions else None
        if not delta:
            return
        newly_done = any(k in DELIVERABLE_KEYS and k not in acc for k in delta)
        acc.update(delta)
        if newly_done:
            save_checkpoint(self.settings, slug, acc)

    async def _resolve_approval(self, payload: dict) -> dict:
        """Get the human decision for a pending approval (or auto-approve)."""
        self._emit({"event": "approval.requested", **payload})
        if self.approval_handler is None:
            decision = {"status": "approved", "comment": "auto-approved (no handler configured)"}
        else:
            result = self.approval_handler(payload)
            decision = await result if asyncio.iscoroutine(result) else result
        self._emit({"event": "approval.resolved", **decision})
        return decision

    # ── Event plumbing ──────────────────────────────────────────────────────────
    def _emit(self, data: dict) -> None:
        """Forward a structured progress event to the sink, if any."""
        if self.on_event:
            self.on_event(data)

    def _emit_event(self, event: Any) -> None:
        """Translate a raw ADK Event into a compact progress dict for the sink."""
        if not self.on_event:
            return
        text = ""
        content = getattr(event, "content", None)
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "text", None):
                text += part.text
        calls = [fc.name for fc in (event.get_function_calls() or [])]
        self.on_event(
            {
                "event": "agent_event",
                "author": getattr(event, "author", None),
                "text_preview": text[:200],
                "tool_calls": calls,
            }
        )
