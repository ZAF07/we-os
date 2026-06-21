"""Stage 0 gate: required-field parsing + DNA/goal validation."""

from __future__ import annotations

import pytest

from marketing_os.errors import GateError
from marketing_os.governance import check_gate, enforce_gate, required_fields, validate_document


def test_required_fields_parsed_from_template(settings):
    labels = required_fields(settings.templates_dir / "customer-dna.md")
    assert "Business name" in labels
    assert "Why customers choose them over alternatives" in labels
    # Recommended-section fields must NOT be treated as required.
    assert "Competitors" not in labels


def test_goal_required_includes_h3_kpi_fields(settings):
    labels = required_fields(settings.templates_dir / "campaign-goal.md")
    assert {"Business KPI", "Marketing KPI", "Creative KPI"} <= set(labels)
    assert "Offer / promotion" not in labels  # Optional section excluded


def test_gate_passes_for_complete_repo(settings):
    report = check_gate(settings, "acme", "acme")
    assert report.ok, report.all_issues


def test_gate_blocks_on_placeholder(settings):
    dna = settings.customers_dir / "acme" / "dna.md"
    dna.write_text(dna.read_text().replace("Acme Climbing Gym", "<name>"), encoding="utf-8")
    report = check_gate(settings, "acme", "acme")
    assert not report.ok
    assert any("Business name" in i for i in report.dna_issues)


def test_gate_blocks_on_missing_files(settings):
    (settings.customers_dir / "acme" / "dna.md").unlink()
    report = check_gate(settings, "acme", "acme")
    assert not report.ok
    assert any("no Customer DNA" in i for i in report.dna_issues)


def test_enforce_gate_raises(settings):
    (settings.campaigns_dir / "acme" / "goal.md").unlink()
    with pytest.raises(GateError) as exc:
        enforce_gate(settings, "acme", "acme")
    assert exc.value.missing  # carries the structured issue list


def test_multiline_field_value_counts_as_filled(settings, tmp_path):
    # A label whose value is written as an indented sub-list underneath it is
    # filled, not empty (matches how the real Customer DNA files are authored).
    doc = tmp_path / "dna.md"
    doc.write_text(
        "# DNA\n\n## Business\n"
        "- **Business name:** Acme\n"
        "- **What they sell:**\n"
        "  - Memberships\n"
        "  - Intro classes\n"
        "\n## Customers\n"
        "- **Primary segment(s):** beginners\n"
        "## Differentiation\n"
        "- **Why customers choose them over alternatives:**\n"
        "  1. Free coached intro\n",
        encoding="utf-8",
    )
    issues = validate_document(settings.templates_dir / "customer-dna.md", doc)
    assert issues == [], issues


def test_validate_document_reports_missing_field(settings, tmp_path):
    bad = tmp_path / "dna.md"
    bad.write_text("# DNA\n\n## Business\n- **What they sell:** widgets\n", encoding="utf-8")
    issues = validate_document(settings.templates_dir / "customer-dna.md", bad)
    assert any("Business name" in i for i in issues)
