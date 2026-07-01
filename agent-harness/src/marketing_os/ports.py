"""Ports — the interfaces the domain and orchestration depend on.

The model and tool ports are LangChain's own ``BaseChatModel`` and ``BaseTool``,
so they are not re-declared here. This module defines the one remaining port that
benefits from an explicit contract: the QA :class:`Reviewer`, which the graph
depends on and which tests substitute with a scripted fake.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .schemas import ReviewVerdict


@runtime_checkable
class Reviewer(Protocol):
    """A QA judge that scores a deliverable against a stage rubric."""

    def review(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Judge a deliverable against the rubric for its stage.

        Args:
            stage_key: The pipeline stage the deliverable belongs to.
            deliverable_text: The full text of the deliverable to review.

        Returns:
            A structured :class:`ReviewVerdict` with the pass/fail decision and
            any discrepancies to resolve.
        """
        ...
