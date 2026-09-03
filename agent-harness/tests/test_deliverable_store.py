"""DeliverableStore contract conformance — the append-only version chain.

The same assertions run against every adapter, because a fake that drifts from
the real store is worse than no fake at all. The Postgres parameter is marked
``slow`` and skips unless ``MARKETING_OS_TEST_POSTGRES=1`` is set.

What is being pinned is the rule ADR-0015 rests on: a revision **appends**. The
prior version stays readable, the feedback that prompted each version is stored
with it, and whether that feedback came from a person or the QA reviewer is
recorded — because the audit trail of *why* a decision changed is the product.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import OTHER_TENANT, SLUG, TENANT
from marketing_os.adapters.deliverables import (
    FilesystemDeliverableStore,
    InMemoryDeliverableStore,
)
from marketing_os.ports import DeliverableStore


@pytest.fixture(
    params=[
        "in-memory",
        "filesystem",
        pytest.param("postgres", marks=pytest.mark.slow),
    ]
)
def store(request: pytest.FixtureRequest, tmp_path: Path) -> DeliverableStore:
    """Build each DeliverableStore adapter for the shared conformance assertions.

    Args:
        request: The parametrized fixture request naming the adapter.
        tmp_path: The pytest temporary directory rooting the filesystem adapter.

    Returns:
        A fresh, empty adapter instance.
    """
    if request.param == "filesystem":
        return FilesystemDeliverableStore(tmp_path)
    if request.param == "postgres":
        from marketing_os.adapters.postgres import PostgresDeliverableStore

        return PostgresDeliverableStore(request.getfixturevalue("postgres_pool"))
    return InMemoryDeliverableStore()


def test_first_append_is_version_one_with_no_feedback(store: DeliverableStore) -> None:
    version = store.append(TENANT, SLUG, "brand-strategy", "# v1")
    assert version.version == 1
    assert version.feedback is None
    assert version.feedback_source is None
    assert version.supersedes_version is None


def test_revision_appends_a_new_version_and_leaves_the_prior_readable(
    store: DeliverableStore,
) -> None:
    store.append(TENANT, SLUG, "brand-strategy", "# v1")
    second = store.append(
        TENANT,
        SLUG,
        "brand-strategy",
        "# v2",
        feedback="Anchor it to convenience.",
        feedback_source="human",
    )

    assert second.version == 2
    assert second.supersedes_version == 1
    assert store.version(TENANT, SLUG, "brand-strategy", 1).content == "# v1"
    assert store.latest(TENANT, SLUG, "brand-strategy").content == "# v2"


def test_each_version_records_the_feedback_that_prompted_it(store: DeliverableStore) -> None:
    store.append(TENANT, SLUG, "brand-strategy", "# v1")
    store.append(
        TENANT, SLUG, "brand-strategy", "# v2", feedback="too premium", feedback_source="human"
    )
    store.append(
        TENANT,
        SLUG,
        "brand-strategy",
        "# v3",
        feedback="rubric point 2",
        feedback_source="reviewer",
    )

    history = store.history(TENANT, SLUG, "brand-strategy")
    assert [(v.version, v.feedback, v.feedback_source) for v in history] == [
        (3, "rubric point 2", "reviewer"),
        (2, "too premium", "human"),
        (1, None, None),
    ]


def test_history_is_newest_first(store: DeliverableStore) -> None:
    for index in range(1, 4):
        store.append(TENANT, SLUG, "research", f"# v{index}")
    assert [v.version for v in store.history(TENANT, SLUG, "research")] == [3, 2, 1]


def test_unwritten_deliverable_has_no_latest_and_no_history(store: DeliverableStore) -> None:
    assert store.latest(TENANT, SLUG, "research") is None
    assert store.history(TENANT, SLUG, "research") == []
    assert store.version(TENANT, SLUG, "research", 1) is None


def test_stages_are_listed_in_pipeline_order(store: DeliverableStore) -> None:
    store.append(TENANT, SLUG, "campaign-strategy", "# c")
    store.append(TENANT, SLUG, "research", "# r")
    store.append(TENANT, SLUG, "brand-strategy", "# b")
    assert store.stages(TENANT, SLUG) == ["research", "brand-strategy", "campaign-strategy"]


def test_versions_are_scoped_to_their_tenant(store: DeliverableStore) -> None:
    store.append(TENANT, SLUG, "research", "# ours")
    assert store.latest(OTHER_TENANT, SLUG, "research") is None
    assert store.stages(OTHER_TENANT, SLUG) == []


def test_versions_are_scoped_to_their_campaign(store: DeliverableStore) -> None:
    store.append(TENANT, SLUG, "research", "# ours")
    assert store.latest(TENANT, "other-campaign", "research") is None


def test_numbering_is_per_stage_not_per_campaign(store: DeliverableStore) -> None:
    store.append(TENANT, SLUG, "research", "# r1")
    store.append(TENANT, SLUG, "research", "# r2")
    first_brand = store.append(TENANT, SLUG, "brand-strategy", "# b1")
    assert first_brand.version == 1
