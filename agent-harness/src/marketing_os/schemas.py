"""Domain schemas — the framework-free data model of the pipeline.

These Pydantic models are the vocabulary the graph, the reviewer, and the
entrypoints share. They carry no LangChain or LangGraph dependency so the domain
core stays testable in isolation. ``ReviewVerdict`` doubles as the structured
output the QA reviewer is asked to return.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
        customer: The customer name the campaign was run for.
        slug: The campaign slug.
        stages: The per-stage results in pipeline order.
        usage: The aggregated token usage across every model call.
        run_log: The repo-relative path of the run's JSONL trace, if written.
    """

    customer: str
    slug: str
    stages: list[StageResult] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    run_log: str | None = None
