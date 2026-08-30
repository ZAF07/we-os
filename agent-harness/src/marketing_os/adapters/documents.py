"""Document storage adapters — where tenant documents physically live.

Implements the :class:`~marketing_os.ports.DocumentStore` port (ADR-0014).
Agents and governance speak markdown and tenant-relative logical paths
(``dna.md``, ``campaigns/<slug>/<name>.md``); the adapter decides where a
document lives.

Every adapter is **tenant-scoped by construction**: the tenant is part of the
physical location, not a filter applied afterwards, so there is no unscoped
query for new code to forget (ADR-0013). The filesystem adapter roots each
tenant at ``tenants/<tenant>/``; the in-memory adapter keys on the tenant. A
Postgres adapter joins the same contract-conformance suite later, backstopped
by row-level security.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from marketing_os.errors import DocumentNotFoundError, ToolError

TENANTS_DIR = "tenants"


def _tenant_relative_segments(path: str) -> list[str]:
    """Normalise a logical document path, refusing anything that escapes its tenant.

    Args:
        path: The tenant-relative logical document path.

    Returns:
        The clean path segments with ``.`` and ``..`` resolved.

    Raises:
        ToolError: If the path is absolute, empty, or climbs above the tenant root.
    """
    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise ToolError(f"Path '{path}' escapes the tenant root.")
    segments: list[str] = []
    for part in pure.parts:
        if part == ".":
            continue
        if part == "..":
            if not segments:
                raise ToolError(f"Path '{path}' escapes the tenant root.")
            segments.pop()
        else:
            segments.append(part)
    if not segments:
        raise ToolError(f"Path '{path}' names no document.")
    return segments


def _tenant_key(tenant: str) -> str:
    """Validate a tenant id for use as a path segment.

    Args:
        tenant: The tenant id derived from the verified identity claim.

    Returns:
        The tenant id unchanged.

    Raises:
        ToolError: If the tenant id is empty or contains path separators, which
            would let one tenant's documents resolve into another's directory.
    """
    cleaned = tenant.strip()
    if not cleaned or "/" in cleaned or "\\" in cleaned or cleaned in {".", ".."}:
        raise ToolError(f"Invalid tenant id: '{tenant}'.")
    return cleaned


class FilesystemDocumentStore:
    """Serves each tenant's documents from its own directory under ``tenants/``.

    The tenant is a path segment, so a document can only ever be reached by
    naming the tenant that owns it: there is no call shape that returns another
    tenant's document, and a logical path attempting to climb out of its tenant
    directory is refused rather than resolved.
    """

    def __init__(self, root: Path) -> None:
        """Initialise the store.

        Args:
            root: The repository root the ``tenants/`` tree lives under.
        """
        self.root = root.resolve()

    def _tenant_root(self, tenant: str) -> Path:
        """Return the directory holding one tenant's documents.

        Args:
            tenant: The tenant the documents belong to.

        Returns:
            The resolved ``tenants/<tenant>/`` directory.
        """
        return (self.root / TENANTS_DIR / _tenant_key(tenant)).resolve()

    def _resolve(self, tenant: str, path: str) -> Path:
        """Map a tenant-relative document path to its filesystem location.

        Args:
            tenant: The tenant the document belongs to.
            path: The tenant-relative document path.

        Returns:
            The resolved absolute path.

        Raises:
            ToolError: If the path escapes the tenant's own directory.
        """
        tenant_root = self._tenant_root(tenant)
        resolved = tenant_root.joinpath(*_tenant_relative_segments(path)).resolve()
        if not resolved.is_relative_to(tenant_root):
            raise ToolError(f"Path '{path}' escapes the tenant root.")
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
    """Holds documents keyed by ``(tenant, path)``; nothing touches the filesystem.

    Keying on the tenant gives the same guarantee as the filesystem adapter's
    per-tenant directory: a lookup that does not name the owning tenant simply
    misses, so the fast test suite exercises the real scoping rule.
    """

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
