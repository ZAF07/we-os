"""Stage 0 — the Brand DNA gate.

Reproduces the orchestrator's three blocking checks:
  1. The tenant's Brand DNA (`dna.md`) exists in the document store.
  2. Every **Required** DNA field is present and not a `<...>` placeholder.
  3. The campaign goal (`campaigns/<slug>/goal.md`) exists with its Required
     fields filled.

Tenant documents resolve through the DocumentStore port. What "Required" means
has two sources, both outside this module so neither can drift from the gate:

  * The **Brand DNA**'s Required fields come from the **published question set**,
    which every caller must name, so publishing a question set with a new
    Required question tightens the gate with no code change (ADR-0018). There is
    no template fallback: an omitted question set is how one entrypoint came to
    enforce a weaker rule than another (ADR-0026).
  * The **campaign goal**'s Required fields always come from
    `templates/campaign-goal.md`, which is code-shipped: the goal is authored per
    campaign and has no questionnaire behind it.

Fails by raising `GateError` with the exact offending fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from marketing_os.config import Settings
from marketing_os.errors import GateError
from marketing_os.markdown import is_placeholder, labels_under_heading, parse_fields
from marketing_os.ports import DocumentStore
from marketing_os.questionnaire import required_dna_fields
from marketing_os.schemas import Questionnaire


def required_fields(template_path: Path) -> list[str]:
    """Return the field labels under the template's ``## Required`` section.

    Args:
        template_path: The code-shipped template to read.

    Returns:
        The Required field labels in document order.

    Raises:
        GateError: If the template is not there to read.
    """
    if not template_path.is_file():
        raise GateError(f"Template not found: {template_path}")
    return labels_under_heading(template_path.read_text(encoding="utf-8"), "Required")


def field_map(doc_text: str) -> dict[str, str]:
    """Map every labelled field in a document to its value.

    Args:
        doc_text: The document text to read.

    Returns:
        Each label mapped to its value; see :mod:`marketing_os.markdown` for the
        multi-line and placeholder rules.
    """
    return parse_fields(doc_text)


def validate_fields(labels: list[str], doc_text: str) -> list[str]:
    """Validate a document against an explicit list of Required field labels.

    The one place a document is checked, whether the labels came from a template
    or from the published question set.

    Args:
        labels: The Required field labels the document must fill.
        doc_text: The document text to validate.

    Returns:
        Human-readable issues, one per missing or placeholder Required field;
        empty when the document passes.
    """
    values = field_map(doc_text)
    issues: list[str] = []
    for label in labels:
        if label not in values:
            issues.append(f"missing Required field: '{label}'")
        elif is_placeholder(values[label]):
            issues.append(f"placeholder/empty Required field: '{label}'")
    return issues


def validate_document(template_path: Path, doc_text: str) -> list[str]:
    """Validate a document's Required fields against its template.

    Args:
        template_path: The template whose ``## Required`` section defines the fields.
        doc_text: The document text to validate.

    Returns:
        Human-readable issues, one per missing or placeholder Required field;
        empty when the document passes.
    """
    return validate_fields(required_fields(template_path), doc_text)


@dataclass
class GateReport:
    """Structured outcome of the Stage 0 gate."""

    tenant: str
    slug: str
    dna_issues: list[str] = field(default_factory=list)
    goal_issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return whether the gate passed with no DNA or goal issues."""
        return not self.dna_issues and not self.goal_issues

    @property
    def all_issues(self) -> list[str]:
        """Return every issue, prefixed by whether it is a DNA or goal issue."""
        return [f"DNA: {i}" for i in self.dna_issues] + [f"Goal: {i}" for i in self.goal_issues]


def check_gate(
    settings: Settings,
    tenant: str,
    slug: str,
    *,
    store: DocumentStore,
    questionnaire: Questionnaire,
) -> GateReport:
    """Run the gate and return a report (does not raise).

    Args:
        settings: The harness settings locating the templates.
        tenant: The tenant the campaign runs for.
        slug: The campaign slug.
        store: The document store the DNA and goal resolve through.
        questionnaire: The published question set. Its Required questions define
            the Required Brand DNA fields, so the questionnaire and the gate
            cannot drift apart.

    Returns:
        The structured gate report.
    """
    dna_document = "dna.md"
    goal_document = f"campaigns/{slug}/goal.md"
    goal_template = settings.templates_dir / "campaign-goal.md"
    dna_labels = required_dna_fields(questionnaire)

    report = GateReport(tenant=tenant, slug=slug)
    if not store.exists(tenant, dna_document):
        report.dna_issues.append(
            f"no Brand DNA at {store.describe(tenant, dna_document)}. Complete the "
            "onboarding questionnaire, answering every Required question."
        )
    else:
        report.dna_issues.extend(validate_fields(dna_labels, store.read(tenant, dna_document)))

    if not store.exists(tenant, goal_document):
        report.goal_issues.append(
            f"no campaign goal at {store.describe(tenant, goal_document)}. Author it from "
            "templates/campaign-goal.md, filling every Required field."
        )
    else:
        report.goal_issues.extend(
            validate_document(goal_template, store.read(tenant, goal_document))
        )
    return report


def enforce_gate(
    settings: Settings,
    tenant: str,
    slug: str,
    *,
    store: DocumentStore,
    questionnaire: Questionnaire,
) -> GateReport:
    """Run the gate and raise GateError if it does not pass.

    Args:
        settings: The harness settings locating the templates.
        tenant: The tenant the campaign runs for.
        slug: The campaign slug.
        store: The document store the DNA and goal resolve through.
        questionnaire: The published question set defining the Required Brand
            DNA fields.

    Returns:
        The passing gate report.

    Raises:
        GateError: If the gate does not pass, carrying the offending fields.
    """
    report = check_gate(settings, tenant, slug, store=store, questionnaire=questionnaire)
    if not report.ok:
        raise GateError(
            "Stage 0 gate failed — work cannot begin until these are fixed:\n  - "
            + "\n  - ".join(report.all_issues),
            missing=report.all_issues,
        )
    return report
