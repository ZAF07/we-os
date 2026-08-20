"""Campaign write scope — the policy guarding every specialist write.

Pure validation enforced in code at the tool layer, never trusted to the
prompt: a specialist may write only campaign documents, and only under the
campaign it is running for. This is the write half of the original filesystem
sandbox, kept storage-agnostic so the same guarantee holds in front of any
:class:`~marketing_os.ports.DocumentStore` adapter.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from marketing_os.errors import ToolError

_WRITE_ROOT = "campaigns"


def _normalise(path: str) -> list[str]:
    """Normalise a repo-relative path into its clean segments.

    Args:
        path: The path the model asked to write.

    Returns:
        The path segments with ``.`` and ``..`` resolved.

    Raises:
        ToolError: If the path is absolute or climbs out of the repository root.
    """
    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise ToolError(f"Path '{path}' escapes the repository root.")
    segments: list[str] = []
    for part in pure.parts:
        if part == ".":
            continue
        if part == "..":
            if not segments:
                raise ToolError(f"Path '{path}' escapes the repository root.")
            segments.pop()
        else:
            segments.append(part)
    return segments


def validate_campaign_write(path: str, slug: str | None) -> str:
    """Validate a specialist write path and return its canonical document path.

    Args:
        path: The repo-relative path the model asked to write.
        slug: The live run slug scoping the write to ``campaigns/<slug>/``, or
            ``None`` to apply only the write-root check.

    Returns:
        The normalised tenant-relative document path.

    Raises:
        ToolError: If the path escapes the repository root, is outside
            ``campaigns/``, or is not under this campaign's directory.
    """
    segments = _normalise(path)
    if not segments or segments[0] != _WRITE_ROOT:
        raise ToolError(
            f"Writes are only permitted under: {_WRITE_ROOT}/. Refused write to '{path}'."
        )
    if slug is not None:
        used = segments[1] if len(segments) > 1 else ""
        if used != slug:
            raise ToolError(
                f"Write path '{path}' is not under this campaign's directory. You "
                f"used the slug '{used}', but this run's slug is '{slug}'. Save the "
                f"deliverable under campaigns/{slug}/ and use the slug '{slug}' "
                "verbatim, character for character — never alter, abbreviate, or "
                "guess it."
            )
    return "/".join(segments)
