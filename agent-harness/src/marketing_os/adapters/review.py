"""QA reviewer — the LLM-as-judge adapter implementing the :class:`Reviewer` port.

Asks a chat model to judge a deliverable against the stage rubric and return a
structured :class:`ReviewVerdict`. Structured output replaces manual JSON parsing,
but the defensive fallback is preserved: if the model fails to produce a valid
verdict, the reviewer fails the iteration with an explicit ``review-format``
discrepancy rather than silently passing.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from marketing_os.config import Settings
from marketing_os.governance.rubric import load_rubric
from marketing_os.schemas import Discrepancy, ReviewVerdict

_REVIEWER_SYSTEM = """\
You are a senior marketing strategist and creative director performing QA. You
review a junior specialist's deliverable against a professional rubric and the
operating principles, and you do not pass work that falls short.

Judge ONLY against the rubric and principles provided. A deliverable passes only
if it satisfies every applicable rubric point: grounded in the Customer DNA,
evidence-based, explains the 'why', ties to the business objective, and stays
within the specialist's remit (no skipping ahead, no inventing strategy).

If the deliverable passes, set passed to true and return no discrepancies.
Otherwise set passed to false and list each violated rubric point with the
specific problem and the concrete fix required.
"""


class LLMReviewer:
    """Scores a deliverable against the stage rubric using a chat model."""

    def __init__(self, model: BaseChatModel, settings: Settings) -> None:
        """Initialise the reviewer.

        Args:
            model: The chat model used to judge deliverables.
            settings: The harness settings locating the rubric files.
        """
        self._model = model.with_structured_output(ReviewVerdict)
        self._settings = settings

    async def areview(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Judge a deliverable against the rubric for its stage.

        The model call is awaited (``ainvoke``) so it runs on the event loop and
        is aborted if the run's task is cancelled mid-flight (see ADR-0009).

        Args:
            stage_key: The pipeline stage the deliverable belongs to.
            deliverable_text: The full text of the deliverable to review.

        Returns:
            A structured verdict; a failing ``review-format`` verdict is returned
            if the model does not produce a valid structured response.
        """
        rubric = load_rubric(self._settings, stage_key)
        user = (
            f"# Review rubric for the '{stage_key}' stage\n\n{rubric}\n\n"
            f"# Deliverable to review\n\n{deliverable_text}\n\n"
            "Return your structured verdict now."
        )
        messages = [SystemMessage(_REVIEWER_SYSTEM), HumanMessage(user)]
        try:
            verdict = await self._model.ainvoke(
                messages, config={"run_name": f"review:{stage_key}"}
            )
        except Exception:
            return self._format_failure()
        if not isinstance(verdict, ReviewVerdict):
            return self._format_failure()
        return verdict

    @staticmethod
    def _format_failure() -> ReviewVerdict:
        """Build the verdict returned when the model output cannot be parsed.

        Returns:
            A failing verdict carrying a single ``review-format`` discrepancy.
        """
        return ReviewVerdict(
            passed=False,
            summary="Reviewer output could not be parsed as a structured verdict.",
            discrepancies=[
                Discrepancy(
                    rubric_point="review-format",
                    problem="The QA reviewer did not return a valid structured verdict.",
                    fix="Re-state the deliverable clearly; the reviewer will re-evaluate.",
                )
            ],
        )
