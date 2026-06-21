"""The Marketing Director — orchestrates the whole pipeline.

Reproduces `/new-campaign`: run the Stage 0 gate, then walk the mandatory
pipeline, delegating each stage to its specialist, running the QA self-critique
loop against the human-written rubrics, and gating advancement on deliverable +
approval. Owns the `campaign-strategy` stage directly (no specialist file exists
for the Director). Never produces assets itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .agents.loader import AgentSpec, load_agent
from .agents.specialist import Specialist
from .config import Settings
from .errors import GuardrailError, PipelineError
from .governance import (
    PIPELINE,
    PIPELINE_BY_KEY,
    Reviewer,
    Stage,
    enforce_gate,
    load_governance,
    prerequisite_met,
)
from .governance.pipeline import DIRECTOR, campaign_dir, deliverable_path
from .loop import AgentLoop, DefaultToolUseLoop, LoopHooks, NoopHooks
from .providers import Provider, provider_from_settings
from .types import ReviewVerdict, StageResult, Usage

# Approval hook signature: decide whether a stage may advance given its verdict.
ApprovalHook = Callable[[str, Path, ReviewVerdict], bool]
EventHook = Callable[[dict], None]

# Inline system body for the Director-owned stage (no .claude/agents file exists
# for the Marketing Director — it is the orchestrator role).
_DIRECTOR_BODY = """\
You are the **Marketing Director** in the Marketing OS specialist hierarchy — the
orchestrator. You own the business goal, campaign strategy, budget allocation, and
KPI planning. You NEVER produce creative assets or generation prompts.

## Your single output
A campaign strategy: the approach, channels-at-a-glance, budget allocation, and the
three KPI tiers (Business / Marketing / Creative), each tied to the business
objective.

## Guardrails (non-negotiable)
- Ground everything in the Customer DNA and the approved brand strategy. Never invent
  what the DNA omits — say so instead.
- Strategy before content: do not specify creative or assets.
- Every decision explains its 'why' and ties back to the business KPI.
- Define all three KPI tiers before recommending spend.
"""


def _default_approval(stage_key: str, path: Path, verdict: ReviewVerdict) -> bool:
    """Default policy: advance only if QA passed."""
    return verdict.passed


def _director_spec() -> AgentSpec:
    return AgentSpec(
        name=DIRECTOR,
        description="Marketing Director — campaign strategy, budget, KPIs.",
        tools=["Read", "Grep", "Glob", "Write"],
        body=_DIRECTOR_BODY,
    )


@dataclass
class CampaignResult:
    customer: str
    slug: str
    stages: list[StageResult]
    usage: Usage


class MarketingDirector:
    """Top-level entrypoint: gate -> pipeline -> per-stage specialist + QA + approval."""

    def __init__(
        self,
        settings: Settings,
        *,
        provider: Optional[Provider] = None,
        web_backend=None,
        approval: ApprovalHook = _default_approval,
        hooks: Optional[LoopHooks] = None,
        loop_factory: Optional[Callable[[], AgentLoop]] = None,
        on_event: Optional[EventHook] = None,
    ) -> None:
        self.settings = settings
        self.provider = provider or provider_from_settings(settings)
        self.web_backend = web_backend
        self.approval = approval
        self.hooks = hooks or NoopHooks()
        self.loop_factory = loop_factory or (lambda: DefaultToolUseLoop(self.hooks))
        self.on_event = on_event
        self.governance = load_governance(settings)
        self.reviewer = Reviewer(self.provider, settings)

    # ── Public API ────────────────────────────────────────────────────────────
    def run_campaign(
        self, customer: str, slug: Optional[str] = None, *, only_stage: Optional[str] = None
    ) -> CampaignResult:
        """Run the full pipeline (or a single stage) for a customer/campaign."""
        slug = slug or customer
        self._emit("gate.start", customer=customer, slug=slug)
        enforce_gate(self.settings, customer, slug)
        self._emit("gate.passed", customer=customer, slug=slug)

        dna_text = (self.settings.customers_dir / customer / "dna.md").read_text(encoding="utf-8")
        campaign_dir(self.settings, slug).mkdir(parents=True, exist_ok=True)

        stages = [PIPELINE_BY_KEY[only_stage]] if only_stage else PIPELINE
        if only_stage and only_stage not in PIPELINE_BY_KEY:
            raise PipelineError(f"Unknown stage '{only_stage}'. Known: {', '.join(PIPELINE_BY_KEY)}.")

        results: list[StageResult] = []
        total = Usage()
        for stage in stages:
            if not prerequisite_met(self.settings, slug, stage):
                raise PipelineError(
                    f"Cannot start stage '{stage.key}': prerequisite '{stage.prerequisite}' "
                    f"does not exist in campaigns/{slug}/. Stages cannot bypass upstream decisions."
                )
            result = self._run_stage(stage, customer, slug, dna_text)
            results.append(result)
            total = total + result.usage
        return CampaignResult(customer=customer, slug=slug, stages=results, usage=total)

    # ── One stage: delegate -> QA loop -> approval ─────────────────────────────
    def _run_stage(self, stage: Stage, customer: str, slug: str, dna_text: str) -> StageResult:
        self._emit("stage.start", stage=stage.key, agent=stage.agent)
        spec = _director_spec() if stage.agent == DIRECTOR else load_agent(self.settings, stage.agent)
        specialist = Specialist(
            spec,
            provider=self.provider,
            sandbox=self._sandbox(),
            governance=self.governance,
            dna_text=dna_text,
            web_backend=self.web_backend,
            loop=self.loop_factory(),
            max_steps=self.settings.max_steps,
            max_tokens=16000,
            stream=self.settings.stream,
        )

        deliverable = deliverable_path(self.settings, slug, stage)
        rel = deliverable.relative_to(self.settings.root)
        task = stage.task.format(
            goal_path=f"campaigns/{slug}/goal.md",
            dna_path=f"customers/{customer}/dna.md",
            prereq_path=(f"campaigns/{slug}/{stage.prerequisite}" if stage.prerequisite else ""),
            deliverable_path=str(rel),
        )

        loop_result = specialist.start(task)
        usage = loop_result.usage
        verdict: Optional[ReviewVerdict] = None
        qa_iterations = 0

        # QA self-critique: read deliverable, review against rubric, revise, repeat.
        while True:
            text = deliverable.read_text(encoding="utf-8") if deliverable.is_file() else None
            if text is None:
                if qa_iterations >= self.settings.max_qa_iterations:
                    raise PipelineError(
                        f"Stage '{stage.key}' did not save its deliverable to {rel} "
                        f"after {qa_iterations} attempts."
                    )
                qa_iterations += 1
                self._emit("stage.save_retry", stage=stage.key, attempt=qa_iterations)
                loop_result = specialist.resume(
                    loop_result.history,
                    f"You have not saved your deliverable. Save it now to {rel} using the "
                    f"write_file tool, then stop.",
                )
                usage = usage + loop_result.usage
                continue

            verdict = self.reviewer.review(stage.key, text)
            self._emit(
                "stage.review",
                stage=stage.key,
                passed=verdict.passed,
                discrepancies=len(verdict.discrepancies),
                iteration=qa_iterations,
            )
            if verdict.passed or qa_iterations >= self.settings.max_qa_iterations:
                break
            qa_iterations += 1
            loop_result = specialist.resume(loop_result.history, verdict.as_revision_instruction())
            usage = usage + loop_result.usage

        approved = self.approval(stage.key, deliverable, verdict)
        if not approved:
            raise GuardrailError(
                f"Stage '{stage.key}' was not approved: QA discrepancies remain unresolved "
                f"after {qa_iterations} revision(s).",
                discrepancies=verdict.discrepancies if verdict else [],
            )

        result = StageResult(
            stage=stage.key,
            deliverable_path=str(rel),
            usage=usage,
            qa_iterations=qa_iterations,
            verdict=verdict,
            approved=approved,
        )
        self._emit("stage.done", stage=stage.key, deliverable=str(rel), qa_iterations=qa_iterations)
        return result

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _sandbox(self):
        from .tools import FilesystemSandbox

        return FilesystemSandbox(self.settings.root, write_prefixes=["campaigns"])

    def _emit(self, event: str, **data) -> None:
        if self.on_event:
            self.on_event({"event": event, **data})
