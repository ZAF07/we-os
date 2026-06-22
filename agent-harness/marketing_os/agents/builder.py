"""Build the ADK agents for each pipeline stage.

Per the worker+formatter split (ADK can't reliably give one agent both tools and
a strict `output_schema`):

- **worker** — a tool-using `LlmAgent` that does the stage's real work and saves
  its prose deliverable to session state under ``<key>_raw`` (and writes the
  markdown file via the filesystem tool). Guardrail callbacks capture its
  per-step DecisionEnvelope.
- **formatter** — a tiny `LlmAgent` with the stage's Pydantic `output_schema`
  that converts ``<key>_raw`` into the strict typed deliverable under ``<key>``.

A stage is `SequentialAgent([worker, formatter])`. The Evaluator is a single
schema agent; an `EscalationGate` ends the refine loop when the Evaluator passes.

Every worker instruction is composed as:
    hard guardrails  +  governance preamble  +  decision-envelope instruction
    +  DNA / overall-goal / current-goal context  +  the role body.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Optional

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from ..config import Settings
from ..guardrails import HARD_GUARDRAILS, load_rubric
from ..guardrails.callbacks import build_callbacks
from ..schemas import STAGE_SCHEMAS
from ..tools import WebBrowser, build_tools
from ..tools.approval import APPROVAL_TOOL_NAME, approval_tool
from ..tools.filesystem import FilesystemTools
from .registry import AgentCfg, RegistryConfig

# Asks every worker to think in the DecisionEnvelope schema before acting, so the
# callbacks can capture a structured per-step trace and the human-check can fire.
_ENVELOPE_INSTRUCTION = """\
Before each tool call or final answer, emit your reasoning as a single fenced
```json block matching this schema, then take the action:
{"thought_summary": str, "next_action": str, "tool_name": str|null,
 "tool_args": object, "reason": str, "expected_observation": str,
 "risk_level": "low"|"medium"|"high", "requires_approval": bool}
Check each step against the overall goal AND your current goal. If an action is
high-risk or you are unsure, set requires_approval=true.
"""

# Closing directive for every worker. ADK only writes a stage's `output_key` when
# the agent's FINAL event has text (llm_agent.py), so a worker that ends on a tool
# call leaves the state var empty and the downstream formatter has nothing to read.
# Requiring the full deliverable as the final message guarantees output_key is set.
_FINAL_OUTPUT_INSTRUCTION = (
    "# Final output (required)\n"
    "After any tool calls — including writing your deliverable file — your FINAL "
    "message MUST be the COMPLETE deliverable content itself, not a summary or a "
    "confirmation like 'done'. It is captured verbatim and handed to the next stage."
)

# Map stage key -> the deliverable filename the worker should write. (The worker
# is also told the path in its prompt; this map mirrors it for reference.)
DELIVERABLE_FILE = {
    "intake": "intake.md",
    "research": "research.md",
    "strategy": "brand-strategy.md",
    "campaign_strategy": "campaign-strategy.md",
    "creative": "creative-brief.md",
    "asset_prompts": "asset-prompts.md",
    "media": "performance-plan.md",
    "execution": "asset-drafts.md",
    "performance": "performance-monitoring.md",
}


@dataclass
class BuildContext:
    """Shared dependencies for building one campaign run's agents.

    Attributes:
        settings: Resolved settings.
        model: The ADK model (LiteLlm) all agents use.
        governance: The `.claude/rules/*.md` preamble text.
        registry: Per-agent tool/human-check config from agents.yaml.
        fs: The run's filesystem tools.
        browser: The run's web browser.
        on_step: Optional live sink for captured step records (CLI/SSE).
    """

    settings: Settings
    model: Any
    governance: str
    registry: RegistryConfig
    fs: FilesystemTools
    browser: WebBrowser
    on_step: Optional[Callable[[dict], None]] = None
    # Whether the active provider supports ADK output_schema (JSON-schema
    # response_format). When False (e.g. DeepSeek), schema agents are prompted for
    # JSON instead of using constrained decoding.
    structured_output: bool = True


# Per-stage one-line "current goal" used for the self-check framing.
_CURRENT_GOAL = {
    "intake": "Produce a clean, structured intake brief.",
    "research": "Gather sourced evidence — findings only.",
    "strategy": "Define positioning and a testable campaign hypothesis.",
    "campaign_strategy": "Set the campaign approach, channels, budget, and KPI tiers.",
    "creative": "Turn the strategy into creative concepts (briefs).",
    "asset_prompts": "Convert the brief into generation prompts (strictly from the brief).",
    "media": "Choose channels, test structure, KPIs, and budget (performance plan).",
    "execution": "Draft concrete assets that follow the approved brief.",
    "performance": "Define monitoring metrics and iteration recommendations.",
}


def _load_prompt(ctx: BuildContext, key: str) -> str:
    """Read a role's instruction body from the packaged prompts dir."""
    return (ctx.settings.prompts_dir / f"{key}.md").read_text(encoding="utf-8").strip()


def _compose_instruction(ctx: BuildContext, key: str, body: str) -> str:
    """Assemble a worker's full system instruction (guardrails + context + role)."""
    return "\n\n".join(
        [
            HARD_GUARDRAILS,
            ctx.governance,
            _ENVELOPE_INSTRUCTION,
            "# Overall goal\n{overall_goal?}",
            f"# Your current goal\n{_CURRENT_GOAL.get(key, '')}",
            "# Customer DNA (ground everything here; never invent what it omits)\n{dna?}",
            body,
            _FINAL_OUTPUT_INSTRUCTION,
        ]
    )


def _build_worker(ctx: BuildContext, cfg: AgentCfg) -> LlmAgent:
    """Build a stage's tool-using worker agent."""
    tools = build_tools(
        cfg.tools,
        fs=ctx.fs,
        browser=ctx.browser,
        confirm=cfg.confirm,
        human_check=cfg.human_check,
    )
    return LlmAgent(
        name=f"{cfg.key}_worker",
        model=ctx.model,
        instruction=_compose_instruction(ctx, cfg.key, _load_prompt(ctx, cfg.key)),
        tools=tools,
        output_key=f"{cfg.key}_raw",
        **build_callbacks(cfg.key, ctx.on_step),
    )


def _json_schema_instruction(schema) -> str:
    """Prompt fragment that asks for raw JSON conforming to a Pydantic schema.

    Used when the provider can't do constrained decoding (no JSON-schema
    response_format), so we constrain via the prompt instead.
    """
    return (
        "\n\nReturn ONLY a single JSON object that conforms to this JSON Schema. "
        "No markdown, no code fences, no commentary before or after.\n\nJSON Schema:\n"
        + json.dumps(schema.model_json_schema())
    )


def _schema_agent(ctx: BuildContext, *, name: str, instruction: str, schema, output_key: str) -> LlmAgent:
    """Build a structured-output agent, provider-aware.

    Uses ADK `output_schema` (constrained decoding) when the active provider
    supports it; otherwise embeds the JSON Schema in the prompt and asks for raw
    JSON. Either way the result lands in `output_key` as JSON text.
    """
    if ctx.structured_output:
        return LlmAgent(
            name=name, model=ctx.model, instruction=instruction,
            output_schema=schema, output_key=output_key,
        )
    return LlmAgent(
        name=name, model=ctx.model,
        instruction=instruction + _json_schema_instruction(schema),
        output_key=output_key,
    )


def _build_formatter(ctx: BuildContext, key: str) -> LlmAgent:
    """Build a stage's structured-output formatter agent (no tools)."""
    return _schema_agent(
        ctx,
        name=f"{key}_formatter",
        instruction=(
            f"You are the formatter for the '{key}' stage. Convert that stage's work "
            f"into the required structured schema. Restructure only — do not add, drop, "
            f"or invent information. Use the deliverable below if present; otherwise use "
            f"the {key} stage's output in the conversation above.\n\n"
            f"Deliverable:\n{{{key}_raw?}}"  # optional ({...?}) so a missing key never crashes
        ),
        schema=STAGE_SCHEMAS[key],
        output_key=key,
    )


def make_skip_if_done(
    label: str, predicate: Callable[[dict], bool]
) -> Callable[[Any], Optional[Any]]:
    """Build a `before_agent_callback` that skips an agent when work is already done.

    Returning content from `before_agent_callback` sets ``end_invocation=True`` on
    that agent's own (copied) invocation context, so only this stage is skipped —
    the parent coordinator proceeds to the next stage. This is what lets a resumed
    run jump straight to where it left off.

    Args:
        label: Stage label, for the skip message.
        predicate: Given the current session state, returns True if this stage's
            work is already present (so it should be skipped).

    Returns:
        An ADK `before_agent_callback` (param MUST be named ``callback_context``).
    """

    def before_agent_callback(callback_context: Any):
        # ADK's State is not a plain mapping (dict(state) raises KeyError: 0); use
        # its to_dict() to get a real dict for the predicate.
        state = callback_context.state
        snapshot = state.to_dict() if hasattr(state, "to_dict") else state
        if predicate(snapshot):
            return genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=f"[resume] '{label}' already complete; skipping.")],
            )
        return None

    return before_agent_callback


def build_stage(
    ctx: BuildContext, key: str, *, skip_if_present: Optional[str] = None
) -> SequentialAgent:
    """Build a worker+formatter stage as a SequentialAgent.

    Args:
        ctx: Shared build dependencies.
        key: Stage key (must be in agents.yaml and STAGE_SCHEMAS).
        skip_if_present: If set, the stage is skipped on resume when this state key
            is already populated (used for the linear top-level stages, not for the
            stages inside the evaluator refine loop, which must re-run each pass).

    Returns:
        A `SequentialAgent` running the worker then the formatter.
    """
    cfg = ctx.registry.agents.get(key, AgentCfg(key=key))
    worker = _build_worker(ctx, cfg)
    formatter = _build_formatter(ctx, key)
    kwargs: dict = {"name": f"{key}_stage", "sub_agents": [worker, formatter]}
    if skip_if_present:
        kwargs["before_agent_callback"] = make_skip_if_done(
            key, lambda s, k=skip_if_present: s.get(k) not in (None, "", [], {})
        )
    return SequentialAgent(**kwargs)


def build_evaluator(ctx: BuildContext) -> LlmAgent:
    """Build the Evaluator: a strict-schema judge (no tools) writing `eval`."""
    rubric = load_rubric(
        ctx.settings,
        "brand-strategy",
        "campaign-strategy",
        "creative-brief",
        "asset-prompts",
        "performance-plan",
    )
    body = _load_prompt(ctx, "evaluator")
    instruction = "\n\n".join(
        [
            HARD_GUARDRAILS,
            ctx.governance,
            "# Overall goal\n{overall_goal?}",
            "# Customer DNA\n{dna?}",
            "# Professional review rubric (editable)\n" + rubric,
            body,
        ]
    )
    return _schema_agent(
        ctx,
        name="evaluator",
        instruction=instruction,
        schema=STAGE_SCHEMAS["evaluator"],
        output_key="eval",
    )


class EscalationGate(BaseAgent):
    """Ends the refine loop once the Evaluator's verdict passes.

    Reads ``state['eval']['passed']``; if true, emits an event with
    ``actions.escalate=True`` so the enclosing `LoopAgent` stops. Otherwise emits
    nothing and the loop runs another refinement pass. Deterministic — no LLM call.
    """

    async def _run_async_impl(self, ctx: Any) -> AsyncGenerator[Event, None]:
        """Escalate iff the latest EvalReport passed."""
        state = getattr(ctx.session, "state", {}) or {}
        verdict = state.get("eval") or {}
        passed = bool(verdict.get("passed")) if isinstance(verdict, dict) else False
        if passed:
            yield Event(author=self.name, actions=EventActions(escalate=True))
        # not passed -> yield nothing; the LoopAgent proceeds to the next iteration


def build_approval_stage(ctx: BuildContext) -> Optional[LlmAgent]:
    """Build the explicit human-approval gate, or None if disabled.

    When enabled (agents.yaml `approval.enabled: true`), this agent's only job is
    to call the long-running `request_human_approval` tool, which pauses the run
    until a human resumes it via the CLI prompt or the API approvals endpoint.
    """
    if not ctx.registry.approval_enabled:
        return None
    return LlmAgent(
        name="approval_gate",
        model=ctx.model,
        instruction=(
            HARD_GUARDRAILS
            + "\n\nThe strategy package has passed evaluation. Summarize it in one or two "
            "sentences, then call `" + APPROVAL_TOOL_NAME + "` to request human sign-off before "
            "execution. Do not produce assets yourself. Wait for the decision."
        ),
        tools=[approval_tool()],
    )
