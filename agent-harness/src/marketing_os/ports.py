"""Ports — the interfaces the domain and orchestration depend on.

The model and tool ports are LangChain's own ``BaseChatModel`` and ``BaseTool``,
so they are not re-declared here. This module defines the remaining ports that
benefit from an explicit contract: the QA :class:`Reviewer`, which the graph
depends on, the :class:`DocumentStore`, which resolves where tenant documents
live (ADR-0014), and the :class:`TokenVerifier`, which establishes who a caller
is (ADR-0013). Tests substitute all three with hermetic fakes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from marketing_os.schemas import ReviewVerdict, VerifiedIdentity


@runtime_checkable
class TokenVerifier(Protocol):
    """Establishes caller identity by verifying a bearer token's signature.

    The engine verifies tokens itself rather than trusting a frontend to have
    done so (ADR-0013), so reaching the engine directly cannot bypass tenancy.
    Implementations are IdP-agnostic: they hold an issuer and a key source, and
    no vendor SDK appears above this port.
    """

    def verify(self, token: str) -> VerifiedIdentity:
        """Verify a bearer token and resolve the identity it carries.

        Args:
            token: The raw bearer token, without its ``Bearer `` prefix.

        Returns:
            The verified identity, including the tenant it acts for.

        Raises:
            UnauthenticatedError: If the token is absent, malformed, expired,
                wrongly signed, issued for another issuer or audience, or
                carries no tenant claim.
        """
        ...


@runtime_checkable
class DocumentStore(Protocol):
    """Tenant-scoped storage for the markdown documents the pipeline reads and writes.

    Documents are addressed by an explicit tenant plus a tenant-relative logical
    path — ``dna.md`` for the Brand DNA, ``campaigns/<slug>/<name>.md`` for
    campaign documents. Markdown stays the agent I/O format; adapters decide
    only where a document physically lives.
    """

    def read(self, tenant: str, path: str) -> str:
        """Return a document's text.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            The document content.

        Raises:
            DocumentNotFoundError: If no such document exists for the tenant.
        """
        ...

    def write(self, tenant: str, path: str, content: str) -> None:
        """Create or replace a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.
            content: The full document text.
        """
        ...

    def exists(self, tenant: str, path: str) -> bool:
        """Return whether a document exists.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            ``True`` if the document exists for the tenant.
        """
        ...

    def list(self, tenant: str, prefix: str) -> list[str]:
        """List the documents under a logical directory prefix.

        Args:
            tenant: The tenant whose documents are listed.
            prefix: The logical directory to list, for example ``campaigns/<slug>``.

        Returns:
            The sorted tenant-relative paths of every document under the prefix.
        """
        ...

    def describe(self, tenant: str, path: str) -> str:
        """Return a human-readable location for a document, for error messages.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            A location string an operator can act on (for the filesystem
            adapter, the absolute path).
        """
        ...


@runtime_checkable
class Reviewer(Protocol):
    """A QA judge that scores a deliverable against a stage rubric."""

    async def areview(self, stage_key: str, deliverable_text: str) -> ReviewVerdict:
        """Judge a deliverable against the rubric for its stage.

        The review runs as an awaited coroutine (per ADR-0009) so the review
        node's LLM call is on the event loop and aborts when the run is cancelled.

        Args:
            stage_key: The pipeline stage the deliverable belongs to.
            deliverable_text: The full text of the deliverable to review.

        Returns:
            A structured :class:`ReviewVerdict` with the pass/fail decision and
            any discrepancies to resolve.
        """
        ...
