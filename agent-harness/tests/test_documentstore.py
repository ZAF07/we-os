"""DocumentStore contract conformance + adapter-specific guarantees.

The conformance tests run identical assertions against every adapter (the
Postgres adapter joins the same suite later). Adapter-specific tests pin what
only one adapter promises: the filesystem adapter reproduces the repository
layout exactly; the in-memory adapter isolates tenants.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from marketing_os.adapters.documents import FilesystemDocumentStore, InMemoryDocumentStore
from marketing_os.errors import DocumentNotFoundError, ToolError
from marketing_os.ports import DocumentStore


@pytest.fixture(params=["filesystem", "in-memory"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> DocumentStore:
    """Build each DocumentStore adapter for the shared conformance assertions.

    Args:
        request: The parametrized fixture request naming the adapter.
        tmp_path: The pytest temporary directory rooting the filesystem adapter.

    Returns:
        A fresh, empty adapter instance.
    """
    if request.param == "filesystem":
        return FilesystemDocumentStore(tmp_path)
    return InMemoryDocumentStore()


def test_write_then_read_round_trips(store: DocumentStore) -> None:
    store.write("acme", "campaigns/spring/research.md", "# Findings")
    assert store.read("acme", "campaigns/spring/research.md") == "# Findings"


def test_read_missing_document_raises(store: DocumentStore) -> None:
    with pytest.raises(DocumentNotFoundError):
        store.read("acme", "campaigns/spring/research.md")


def test_exists_reflects_writes(store: DocumentStore) -> None:
    assert store.exists("acme", "campaigns/spring/goal.md") is False
    store.write("acme", "campaigns/spring/goal.md", "# Goal")
    assert store.exists("acme", "campaigns/spring/goal.md") is True


def test_overwrite_replaces_content(store: DocumentStore) -> None:
    store.write("acme", "campaigns/spring/goal.md", "v1")
    store.write("acme", "campaigns/spring/goal.md", "v2")
    assert store.read("acme", "campaigns/spring/goal.md") == "v2"


def test_list_returns_sorted_documents_under_a_prefix(store: DocumentStore) -> None:
    store.write("acme", "campaigns/spring/research.md", "r")
    store.write("acme", "campaigns/spring/brand-strategy.md", "b")
    store.write("acme", "campaigns/other/goal.md", "g")
    listed = store.list("acme", "campaigns/spring")
    assert listed == [
        "campaigns/spring/brand-strategy.md",
        "campaigns/spring/research.md",
    ]


def test_list_unknown_prefix_is_empty(store: DocumentStore) -> None:
    assert store.list("acme", "campaigns/nothing-here") == []


def test_dna_document_round_trips_per_tenant(store: DocumentStore) -> None:
    store.write("acme", "dna.md", "# Brand DNA — Acme")
    assert store.exists("acme", "dna.md") is True
    assert store.read("acme", "dna.md") == "# Brand DNA — Acme"


def test_describe_names_a_human_readable_location(store: DocumentStore) -> None:
    assert "dna.md" in store.describe("acme", "dna.md")


def test_filesystem_layout_matches_the_repository(tmp_path: Path) -> None:
    fs = FilesystemDocumentStore(tmp_path)
    fs.write("acme", "dna.md", "# DNA")
    fs.write("acme", "campaigns/spring/research.md", "# Findings")
    assert (tmp_path / "customers" / "acme" / "dna.md").read_text(encoding="utf-8") == "# DNA"
    assert (tmp_path / "campaigns" / "spring" / "research.md").is_file()
    assert fs.describe("acme", "dna.md") == str(tmp_path / "customers" / "acme" / "dna.md")


def test_filesystem_rejects_paths_escaping_the_root(tmp_path: Path) -> None:
    fs = FilesystemDocumentStore(tmp_path)
    with pytest.raises(ToolError):
        fs.write("acme", "../outside.md", "nope")
    assert not (tmp_path.parent / "outside.md").exists()


def test_in_memory_isolates_tenants() -> None:
    memory = InMemoryDocumentStore()
    memory.write("acme", "campaigns/spring/research.md", "# Findings")
    memory.write("acme", "dna.md", "# DNA")
    assert memory.exists("rival", "campaigns/spring/research.md") is False
    assert memory.list("rival", "campaigns/spring") == []
    with pytest.raises(DocumentNotFoundError):
        memory.read("rival", "dna.md")
