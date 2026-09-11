"""The ask tool — how a specialist asks the business for a fact it lacks.

A specialist working a stage sometimes needs a fact the Brand DNA never
captured. It must never infer it (ADR-0028): it calls ``ask_tenant`` with every
question it is missing, the tool raises :class:`ClarificationRequested`, the
specialist's loop ends at once, and the graph halts the stage until the
business answers in the app.

The tool's description carries the same rule the Questionnaire does — ask only
for facts the owner uniquely knows, never for anything the pipeline itself owes
the business — because the description is the one place the model reads the
rule at the moment it decides what to ask.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from marketing_os.errors import ClarificationRequested
from marketing_os.schemas import ClarificationQuestion

ASK_TENANT_TOOL = "ask_tenant"


def ask_tenant_tool() -> BaseTool:
    """Build the tool every specialist uses to ask the business for a missing fact.

    Returns:
        The ``ask_tenant`` LangChain tool.
    """

    @tool(ASK_TENANT_TOOL, parse_docstring=True)
    def ask_tenant(questions: list[ClarificationQuestion]) -> str:
        """Ask the business owner for facts the Brand DNA lacks; the run halts until they answer.

        Use this when a recommendation would rest on something only the business
        owner knows and the Brand DNA does not say — whether they have an email
        list, what their opening hours are, which areas they can deliver to. Do
        not infer such a fact and do not write a deliverable that quietly assumes
        it: a recommendation resting on a fact absent from the Brand DNA fails
        review.

        The rule is the Questionnaire's own. Ask only for facts the owner
        uniquely knows. Never ask for positioning, messaging, brand voice, a
        value proposition, channel choice, or anything else the pipeline owes
        the business — those are your job. Batch every fact you are missing into
        one call, since each call restarts this stage once the answers arrive.

        Args:
            questions: Every fact you need, each as a plain question to the owner
                with a short reason saying why this stage needs it.

        Returns:
            Nothing: calling this ends your turn and halts the stage.

        Raises:
            ClarificationRequested: Always; the graph turns it into the halt.
        """
        raise ClarificationRequested(
            [ClarificationQuestion.model_validate(question) for question in questions]
        )

    return ask_tenant
