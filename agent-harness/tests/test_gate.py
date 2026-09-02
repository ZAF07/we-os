"""Stage 0 gate: required-field parsing + DNA/goal validation."""

from __future__ import annotations

import pytest

from conftest import SLUG, TENANT
from marketing_os.adapters.documents import FilesystemDocumentStore, InMemoryDocumentStore
from marketing_os.errors import GateError
from marketing_os.governance import check_gate, enforce_gate, required_fields, validate_document


def _store(settings) -> FilesystemDocumentStore:
    """Build the filesystem document store rooted at the test repo.

    Args:
        settings: The harness settings fixture.

    Returns:
        The filesystem adapter over the hermetic repo.
    """
    return FilesystemDocumentStore(settings.root)


def test_required_fields_parsed_from_template(settings):
    labels = required_fields(settings.templates_dir / "brand-dna.md")
    assert "Business name" in labels
    assert "Why customers choose them over alternatives" in labels
    # Recommended-section fields must NOT be treated as required.
    assert "Competitors" not in labels


def test_goal_required_includes_h3_kpi_fields(settings):
    labels = required_fields(settings.templates_dir / "campaign-goal.md")
    assert {"Business KPI", "Marketing KPI", "Creative KPI"} <= set(labels)
    assert "Offer / promotion" not in labels  # Optional section excluded


def test_gate_passes_for_complete_repo(settings):
    report = check_gate(settings, TENANT, SLUG, store=_store(settings))
    assert report.ok, report.all_issues


def test_gate_blocks_on_placeholder(settings):
    dna = settings.tenant_dir(TENANT) / "dna.md"
    dna.write_text(dna.read_text().replace("Acme Climbing Gym", "<name>"), encoding="utf-8")
    report = check_gate(settings, TENANT, SLUG, store=_store(settings))
    assert not report.ok
    assert any("Business name" in i for i in report.dna_issues)


def test_gate_blocks_on_missing_files(settings):
    (settings.tenant_dir(TENANT) / "dna.md").unlink()
    report = check_gate(settings, TENANT, SLUG, store=_store(settings))
    assert not report.ok
    assert any("no Brand DNA" in i for i in report.dna_issues)


def test_gate_runs_against_an_in_memory_store(settings):
    memory = InMemoryDocumentStore()
    memory.write(TENANT, "dna.md", (settings.tenant_dir(TENANT) / "dna.md").read_text())
    report = check_gate(settings, TENANT, SLUG, store=memory)
    assert report.dna_issues == []
    assert any("no campaign goal" in i for i in report.goal_issues)


def test_enforce_gate_raises(settings):
    (settings.tenant_dir(TENANT) / "campaigns" / SLUG / "goal.md").unlink()
    with pytest.raises(GateError) as exc:
        enforce_gate(settings, TENANT, SLUG, store=_store(settings))
    assert exc.value.missing  # carries the structured issue list


def test_multiline_field_value_counts_as_filled(settings):
    # A label whose value is written as an indented sub-list underneath it is
    # filled, not empty (matches how the real Brand DNA files are authored).
    doc_text = (
        "# DNA\n\n## Business\n"
        "- **Business name:** Acme\n"
        "- **What they sell:**\n"
        "  - Memberships\n"
        "  - Intro classes\n"
        "\n## Customers\n"
        "- **Primary segment(s):** beginners\n"
        "## Differentiation\n"
        "- **Why customers choose them over alternatives:**\n"
        "  1. Free coached intro\n"
    )
    issues = validate_document(settings.templates_dir / "brand-dna.md", doc_text)
    assert issues == [], issues


def test_validate_document_reports_missing_field(settings):
    bad_text = "# DNA\n\n## Business\n- **What they sell:** widgets\n"
    issues = validate_document(settings.templates_dir / "brand-dna.md", bad_text)
    assert any("Business name" in i for i in issues)


def test_gate_derives_required_dna_fields_from_the_question_set(settings):
    # Adding a Required question tightens the gate with no code change: the DNA
    # in the repo answers the template's fields but not this new one.
    from marketing_os.questionnaire import SEED_QUESTIONNAIRE
    from marketing_os.schemas import Question, Questionnaire

    added = Question(
        id="q_seasonality",
        field="Seasonality",
        section="Reach & constraints",
        text="When is your busiest season?",
        why_we_ask="Timing changes the message.",
        help_text="Name the months.",
        required=True,
    )
    tightened = Questionnaire(
        version=SEED_QUESTIONNAIRE.version + 1,
        published_at="2026-09-02T09:00:00Z",
        questions=[*SEED_QUESTIONNAIRE.questions, added],
    )
    report = check_gate(settings, TENANT, SLUG, store=_store(settings), questionnaire=tightened)
    assert not report.ok
    assert any("Seasonality" in issue for issue in report.dna_issues)


def test_gate_ignores_the_template_when_a_question_set_is_supplied(settings):
    # The published question set is authoritative for the DNA half of the gate,
    # so a DNA answering every published Required question passes even though
    # the template names fields the question set does not (ADR-0018).
    from marketing_os.questionnaire import SEED_QUESTIONNAIRE, render_brand_dna
    from marketing_os.schemas import BrandDnaRecord, DnaAnswer

    record = BrandDnaRecord(
        questionnaire_version=SEED_QUESTIONNAIRE.version,
        answers=[
            DnaAnswer(question_id=question.id, answer=f"Answer to {question.field}")
            for question in SEED_QUESTIONNAIRE.required_questions
        ],
    )
    store = InMemoryDocumentStore()
    store.write(TENANT, "dna.md", render_brand_dna(SEED_QUESTIONNAIRE, record, business_name="A"))
    store.write(
        TENANT,
        f"campaigns/{SLUG}/goal.md",
        (settings.tenant_dir(TENANT) / "campaigns" / SLUG / "goal.md").read_text(),
    )
    report = check_gate(settings, TENANT, SLUG, store=store, questionnaire=SEED_QUESTIONNAIRE)
    assert report.ok, report.all_issues
