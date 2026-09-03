"""Deliverable version adapters — where a deliverable's history physically lives.

Implements the :class:`~marketing_os.ports.DeliverableStore` port (ADR-0015).
The store is **append-only**: a revision writes a new version rather than
replacing the last, so the prior version stays readable and the feedback that
prompted each one is recorded alongside it. Nothing in this module deletes or
edits a stored version.

Like the document adapters, every adapter here is tenant-scoped by construction
— the tenant is part of the physical location rather than a filter applied
afterwards (ADR-0013). The filesystem adapter keeps one JSON file per stage
under ``tenants/<tenant>/campaigns/<slug>/.versions/``, which keeps the history
beside the campaign it belongs to without polluting the deliverable listing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from marketing_os.adapters.documents import validate_tenant_id
from marketing_os.governance.pipeline import PIPELINE
from marketing_os.schemas import DeliverableVersion

VERSIONS_DIR = ".versions"

HUMAN_FEEDBACK = "human"
REVIEWER_FEEDBACK = "reviewer"

_STAGE_ORDER = {stage.key: index for index, stage in enumerate(PIPELINE)}


def now_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 timestamp.

    Returns:
        The timestamp every adapter stamps a new version with, so the format is
        identical whichever store is behind the port.
    """
    return datetime.now(UTC).isoformat()


def in_pipeline_order(stage_keys: list[str]) -> list[str]:
    """Sort stage keys into mandatory pipeline order.

    Args:
        stage_keys: The stage keys to sort, in any order.

    Returns:
        The keys in pipeline order; keys the pipeline does not know are last.
    """
    return sorted(stage_keys, key=lambda key: _STAGE_ORDER.get(key, len(_STAGE_ORDER)))


def next_version(
    history: list[DeliverableVersion],
    stage_key: str,
    content: str,
    feedback: str | None,
    feedback_source: str | None,
) -> DeliverableVersion:
    """Build the version that follows an existing history.

    Shared by every adapter so the numbering and the ``supersedes_version``
    chain are decided in one place rather than re-derived per backend.

    Args:
        history: The stage's existing versions, in any order.
        stage_key: The stage the deliverable belongs to.
        content: The full deliverable markdown.
        feedback: The feedback that prompted this version, if any.
        feedback_source: ``human`` or ``reviewer``, if any.

    Returns:
        The next version, numbered one past the highest already stored.
    """
    highest = max((version.version for version in history), default=0)
    return DeliverableVersion(
        stage_key=stage_key,
        version=highest + 1,
        content=content,
        created_at=now_timestamp(),
        feedback=feedback,
        feedback_source=feedback_source,
        supersedes_version=highest or None,
    )


class VersionHistoryReader:
    """The three read operations every local adapter shares over a version list.

    ``latest``, ``version`` and ``history`` are the same three shapes over one
    stage's stored versions; only *where the list comes from* differs between the
    in-memory and filesystem adapters. Subclasses supply :meth:`_load` and inherit
    the readers, so the three cannot drift apart between backends.
    """

    def _load(self, tenant: str, slug: str, stage_key: str) -> list[DeliverableVersion]:
        """Return one stage's stored versions in the order they were appended.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose versions to load.

        Returns:
            The stored versions, empty when the stage has produced none.

        Raises:
            NotImplementedError: Always; every subclass supplies its own.
        """
        raise NotImplementedError

    def latest(self, tenant: str, slug: str, stage_key: str) -> DeliverableVersion | None:
        """Return the newest version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable to read.

        Returns:
            The newest version, or ``None`` when the stage has produced none.
        """
        stored = self._load(tenant, slug, stage_key)
        return stored[-1] if stored else None

    def version(
        self, tenant: str, slug: str, stage_key: str, version: int
    ) -> DeliverableVersion | None:
        """Return one historical version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable to read.
            version: The version number to read.

        Returns:
            That version, or ``None`` when it was never written.
        """
        stored = self._load(tenant, slug, stage_key)
        return next((item for item in stored if item.version == version), None)

    def history(self, tenant: str, slug: str, stage_key: str) -> list[DeliverableVersion]:
        """Return every version of a stage's deliverable, newest first.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose history to read.

        Returns:
            The versions newest first, empty when the stage has produced none.
        """
        return sorted(
            self._load(tenant, slug, stage_key), key=lambda item: item.version, reverse=True
        )


class InMemoryDeliverableStore(VersionHistoryReader):
    """Holds version histories keyed by ``(tenant, slug, stage_key)``.

    The fast suite's store and the single-worker default. It enforces the same
    append-only numbering as the Postgres store, so every behaviour except
    surviving a restart is exercised without a database.
    """

    def __init__(self) -> None:
        """Initialise the empty store."""
        self._versions: dict[tuple[str, str, str], list[DeliverableVersion]] = {}

    def append(
        self,
        tenant: str,
        slug: str,
        stage_key: str,
        content: str,
        *,
        feedback: str | None = None,
        feedback_source: str | None = None,
    ) -> DeliverableVersion:
        """Append a new version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable this is.
            content: The full deliverable markdown.
            feedback: The feedback that prompted this version, if any.
            feedback_source: ``human`` or ``reviewer``, if any.

        Returns:
            The stored version, carrying the number it was assigned.
        """
        key = (tenant, slug, stage_key)
        stored = self._versions.setdefault(key, [])
        version = next_version(stored, stage_key, content, feedback, feedback_source)
        stored.append(version)
        return version

    def _load(self, tenant: str, slug: str, stage_key: str) -> list[DeliverableVersion]:
        """Return one stage's stored versions in the order they were appended.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose versions to load.

        Returns:
            The stored versions, empty when the stage has produced none.
        """
        return list(self._versions.get((tenant, slug, stage_key), []))

    def stages(self, tenant: str, slug: str) -> list[str]:
        """Return the stage keys a campaign has produced a deliverable for.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The stage keys in mandatory pipeline order.
        """
        return in_pipeline_order(
            [
                stage_key
                for owner, campaign, stage_key in self._versions
                if owner == tenant and campaign == slug
            ]
        )


class FilesystemDeliverableStore(VersionHistoryReader):
    """Keeps each stage's version history as one JSON file beside its campaign.

    The history lives under ``tenants/<tenant>/campaigns/<slug>/.versions/`` so
    it sits with the campaign it describes while staying out of the deliverable
    listing, which serves ``*.md`` only. This is the local-development store;
    Postgres is the system of record in a deployment (ADR-0014).
    """

    def __init__(self, root: Path) -> None:
        """Initialise the store.

        Args:
            root: The repository root the ``tenants/`` tree lives under.
        """
        self._root = Path(root)

    def _history_file(self, tenant: str, slug: str, stage_key: str) -> Path:
        """Return the JSON file holding one stage's version history.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose history file to locate.

        Returns:
            The history file's path, which need not exist yet.
        """
        scoped = validate_tenant_id(tenant)
        campaign = self._root / "tenants" / scoped / "campaigns" / slug
        return campaign / VERSIONS_DIR / f"{stage_key}.json"

    def _load(self, tenant: str, slug: str, stage_key: str) -> list[DeliverableVersion]:
        """Return one stage's stored versions in the order they were appended.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose versions to load.

        Returns:
            The stored versions, empty when the stage has produced none.
        """
        path = self._history_file(tenant, slug, stage_key)
        if not path.is_file():
            return []
        records = json.loads(path.read_text(encoding="utf-8"))
        return [DeliverableVersion(**record) for record in records]

    def append(
        self,
        tenant: str,
        slug: str,
        stage_key: str,
        content: str,
        *,
        feedback: str | None = None,
        feedback_source: str | None = None,
    ) -> DeliverableVersion:
        """Append a new version of a stage's deliverable.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.
            stage_key: The stage whose deliverable this is.
            content: The full deliverable markdown.
            feedback: The feedback that prompted this version, if any.
            feedback_source: ``human`` or ``reviewer``, if any.

        Returns:
            The stored version, carrying the number it was assigned.
        """
        path = self._history_file(tenant, slug, stage_key)
        stored = self._load(tenant, slug, stage_key)
        version = next_version(stored, stage_key, content, feedback, feedback_source)
        stored.append(version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([item.model_dump() for item in stored], indent=2),
            encoding="utf-8",
        )
        return version

    def stages(self, tenant: str, slug: str) -> list[str]:
        """Return the stage keys a campaign has produced a deliverable for.

        Args:
            tenant: The tenant that owns the campaign.
            slug: The campaign slug.

        Returns:
            The stage keys in mandatory pipeline order.
        """
        scoped = validate_tenant_id(tenant)
        directory = self._root / "tenants" / scoped / "campaigns" / slug / VERSIONS_DIR
        if not directory.is_dir():
            return []
        return in_pipeline_order([path.stem for path in directory.glob("*.json")])


def human_revisions_used(versions: list[DeliverableVersion]) -> int:
    """Count how many times a person has sent a deliverable back.

    The revision cap counts a *person's* refusals, not every version: the QA
    reviewer's own revision rounds are already bounded by its own budget, and
    charging them against the owner's allowance would refuse their first real
    revision (ADR-0015). Counting here rather than at each call site is what
    keeps the number the gate reports and the number the cap enforces identical.

    Args:
        versions: The deliverable's versions, in any order.

    Returns:
        How many versions a person's feedback prompted.
    """
    return sum(1 for version in versions if version.feedback_source == HUMAN_FEEDBACK)
