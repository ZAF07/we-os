"""Provider-agnostic data types shared across the harness.

These are the normalized representations the agent loop and orchestrator work
with. Each provider adapter translates between these and its own SDK's wire
format, so nothing above the adapter layer ever sees a provider-specific shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    """A request from the model to invoke a tool."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """The outcome of executing a ToolCall, fed back to the model."""

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class Usage:
    """Token accounting for one or more completions (provider-normalized)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens
            + other.cache_read_input_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens
            + other.cache_creation_input_tokens,
        )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class Message:
    """A single turn in the conversation.

    `provider_native` carries the raw, provider-specific content (e.g. Anthropic
    content blocks, including thinking blocks) so an assistant turn can be replayed
    back to the same provider verbatim. The agent loop never inspects it; only the
    adapter that produced it reads it back, and only when `provider` matches.
    """

    role: str  # "system" | "user" | "assistant" | "tool"
    content: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Set on a tool-result message:
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    is_error: bool = False
    # Round-trip fidelity (adapter-owned, opaque above the provider layer):
    provider_native: Any = None
    provider: Optional[str] = None

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)

    @classmethod
    def from_tool_result(cls, result: ToolResult, name: str | None = None) -> "Message":
        return cls(
            role="tool",
            content=result.content,
            tool_call_id=result.tool_call_id,
            name=name,
            is_error=result.is_error,
        )


@dataclass
class CompletionResult:
    """What a provider returns from one `complete()` call."""

    text: str
    tool_calls: list[ToolCall]
    stop_reason: str  # normalized: "end_turn" | "tool_use" | "max_tokens" | "refusal"
    usage: Usage
    assistant_message: Message  # ready to append to history verbatim


@dataclass
class Discrepancy:
    """One issue the QA reviewer found between a deliverable and the rubric."""

    rubric_point: str
    problem: str
    fix: str


@dataclass
class ReviewVerdict:
    """The QA reviewer's structured judgement of a deliverable."""

    passed: bool
    discrepancies: list[Discrepancy] = field(default_factory=list)
    summary: str = ""

    def as_revision_instruction(self) -> str:
        """Render the discrepancies as a revision brief for the specialist."""
        lines = [
            "Your deliverable did not fully satisfy the professional review rubric. "
            "Revise it to resolve every item below. Keep everything that already "
            "passes; change only what is needed.",
            "",
        ]
        for i, d in enumerate(self.discrepancies, 1):
            lines.append(f"{i}. [{d.rubric_point}] {d.problem}")
            if d.fix:
                lines.append(f"   Fix: {d.fix}")
        return "\n".join(lines)


@dataclass
class StageResult:
    """Outcome of running one pipeline stage end-to-end (agent + QA + approval)."""

    stage: str
    deliverable_path: str
    usage: Usage
    qa_iterations: int
    verdict: Optional[ReviewVerdict] = None
    approved: bool = True
