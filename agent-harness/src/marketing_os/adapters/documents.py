"""Document storage adapters — where tenant documents physically live.

Implements the :class:`~marketing_os.ports.DocumentStore` port (ADR-0014).
Agents and governance speak markdown and tenant-relative logical paths; the
adapter decides where a document lives. The filesystem adapter reproduces the
repository layout exactly — ``dna.md`` resolves to ``customers/<tenant>/dna.md``
and campaign documents stay under ``campaigns/`` — so local development is
unchanged. The in-memory adapter backs the fast test suite with nothing on
disk. A Postgres adapter joins the same contract-conformance suite later.
"""

from __future__ import annotations

from pathlib import Path

from marketing_os.errors import DocumentNotFoundError, ToolError

_DNA_DOCUMENT = "dna.md"
_CUSTOMERS_DIR = "customers"


class FilesystemDocumentStore:
    """Serves documents from the repository filesystem in today's exact layout.

    This is the single-tenant local-development layout: only the Brand DNA is
    mapped per tenant (``customers/<tenant>/dna.md``); campaign paths resolve
    to the shared ``campaigns/`` tree regardless of tenant. Real tenant
    isolation is the Postgres adapter's job (ADR-0014).
    """

    def __init__(self, root: Path) -> None:
        """Initialise the store.

        Args:
            root: The repository root all documents resolve under.
        """
        self.root = root.resolve()

    def _resolve(self, tenant: str, path: str) -> Path:
        """Map a tenant-relative document path to its filesystem location.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            The resolved absolute path.

        Raises:
            ToolError: If the path escapes the repository root.
        """
        if path == _DNA_DOCUMENT:
            resolved = (self.root / _CUSTOMERS_DIR / tenant / _DNA_DOCUMENT).resolve()
        else:
            resolved = (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            raise ToolError(f"Path '{path}' escapes the repository root.")
        return resolved

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
        resolved = self._resolve(tenant, path)
        if not resolved.is_file():
            raise DocumentNotFoundError(f"Document not found: {path}")
        return resolved.read_text(encoding="utf-8")

    def write(self, tenant: str, path: str, content: str) -> None:
        """Create or replace a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.
            content: The full document text.
        """
        resolved = self._resolve(tenant, path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

    def exists(self, tenant: str, path: str) -> bool:
        """Return whether a document exists.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            ``True`` if the document exists for the tenant.
        """
        return self._resolve(tenant, path).is_file()

    def list(self, tenant: str, prefix: str) -> list[str]:
        """List the documents under a logical directory prefix.

        Args:
            tenant: The tenant whose documents are listed.
            prefix: The logical directory to list, for example ``campaigns/<slug>``.

        Returns:
            The sorted tenant-relative paths of every document under the prefix.
        """
        base = self._resolve(tenant, prefix)
        if not base.is_dir():
            return []
        return sorted(
            f"{prefix.rstrip('/')}/{found.relative_to(base).as_posix()}"
            for found in base.rglob("*")
            if found.is_file()
        )

    def describe(self, tenant: str, path: str) -> str:
        """Return the absolute filesystem path of a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            The absolute path as a string.
        """
        return str(self._resolve(tenant, path))


class InMemoryDocumentStore:
    """Holds documents in a per-tenant dict; nothing touches the filesystem."""

    def __init__(self) -> None:
        """Initialise the empty store."""
        self._documents: dict[tuple[str, str], str] = {}

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
        try:
            return self._documents[(tenant, path)]
        except KeyError as exc:
            raise DocumentNotFoundError(f"Document not found: {path}") from exc

    def write(self, tenant: str, path: str, content: str) -> None:
        """Create or replace a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.
            content: The full document text.
        """
        self._documents[(tenant, path)] = content

    def exists(self, tenant: str, path: str) -> bool:
        """Return whether a document exists.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            ``True`` if the document exists for the tenant.
        """
        return (tenant, path) in self._documents

    def list(self, tenant: str, prefix: str) -> list[str]:
        """List the documents under a logical directory prefix.

        Args:
            tenant: The tenant whose documents are listed.
            prefix: The logical directory to list, for example ``campaigns/<slug>``.

        Returns:
            The sorted tenant-relative paths of every document under the prefix.
        """
        directory = prefix.rstrip("/") + "/"
        return sorted(
            path
            for owner, path in self._documents
            if owner == tenant and path.startswith(directory)
        )

    def describe(self, tenant: str, path: str) -> str:
        """Return a human-readable in-memory location for a document.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            An ``in-memory:<tenant>/<path>`` location string.
        """
        return f"in-memory:{tenant}/{path}"
