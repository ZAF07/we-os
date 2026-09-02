"""Stage 0 — the Brand DNA gate.

Reproduces the orchestrator's three blocking checks:
  1. The tenant's Brand DNA (`dna.md`) exists in the document store.
  2. Every **Required** DNA field is present and not a `<...>` placeholder.
  3. The campaign goal (`campaigns/<slug>/goal.md`) exists with its Required
     fields filled.

Tenant documents resolve through the DocumentStore port. What "Required" means
has two sources, both outside this module so neither can drift from the gate:

  * The **Brand DNA**'s Required fields come from the **published question set**
    when one is supplied, so publishing a question set with a new Required
    question tightens the gate with no code change (ADR-0018). Without one — the
    CLI, and any caller with no questionnaire store — it falls back to
    `templates/brand-dna.md`, which is the same rule against the hand-authored
    template.
  * The **campaign goal**'s Required fields always come from
    `templates/campaign-goal.md`, which is code-shipped: the goal is authored per
    campaign and has no questionnaire behind it.

Fails by raising `GateError` with the exact offending fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from marketing_os.config import Settings
from marketing_os.errors import GateError
from marketing_os.ports import DocumentStore
from marketing_os.questionnaire import required_dna_fields
from marketing_os.schemas import Questionnaire

_FIELD_RE = re.compile(r"^\s*-\s*\*\*(.+?):\*\*\s*(.*)$")
_PLACEHOLDER_RE = re.compile(r"^<[^>]*>$")


def required_fields(template_path: Path) -> list[str]:
    """Field labels under the template's `## Required` section."""
    if not template_path.is_file():
        raise GateError(f"Template not found: {template_path}")
    labels: list[str] = []
    in_required = False
    for line in template_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## Required"):
            in_required = True
            continue
        if in_required and stripped.startswith("## ") and not stripped.startswith("## Required"):
            break  # next H2 ends the Required block (H3 subsections stay inside)
        if in_required:
            m = _FIELD_RE.match(line)
            if m:
                labels.append(m.group(1).strip())
    return labels


def field_map(doc_text: str) -> dict[str, str]:
    """Map every `- **Label:**` field to its value block.

    A field's value is the text on the same line PLUS any following lines
    (indented sub-bullets, numbered lists, continuation prose) up to the next
    field line or markdown heading. This means a label whose value is written as
    a multi-line list underneath it counts as filled, not empty.
    """
    out: dict[str, str] = {}
    label: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if label is not None:
            out[label] = "\n".join(parts).strip()

    for line in doc_text.splitlines():
        m = _FIELD_RE.match(line)
        if m:
            flush()
            label = m.group(1).strip()
            parts = [m.group(2)]
        elif line.lstrip().startswith("#"):
            flush()
            label, parts = None, []
        elif label is not None:
            parts.append(line)
    flush()
    return out


def _is_placeholder(value: str) -> bool:
    v = value.strip()
    # Empty, or a single unfilled angle-bracket placeholder like "<name>".
    return v == "" or bool(_PLACEHOLDER_RE.match(v))


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
        elif _is_placeholder(values[label]):
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
    questionnaire: Questionnaire | None = None,
) -> GateReport:
    """Run the gate and return a report (does not raise).

    Args:
        settings: The harness settings locating the templates.
        tenant: The tenant the campaign runs for.
        slug: The campaign slug.
        store: The document store the DNA and goal resolve through.
        questionnaire: The published question set, when the caller has one. Its
            Required questions define the Required Brand DNA fields, so the
            questionnaire and the gate cannot drift apart. Omitted, the gate
            falls back to the hand-authoring template.

    Returns:
        The structured gate report.
    """
    dna_document = "dna.md"
    goal_document = f"campaigns/{slug}/goal.md"
    goal_template = settings.templates_dir / "campaign-goal.md"
    dna_labels = (
        required_dna_fields(questionnaire)
        if questionnaire is not None
        else required_fields(settings.templates_dir / "brand-dna.md")
    )

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
    questionnaire: Questionnaire | None = None,
) -> GateReport:
    """Run the gate and raise GateError if it does not pass.

    Args:
        settings: The harness settings locating the templates.
        tenant: The tenant the campaign runs for.
        slug: The campaign slug.
        store: The document store the DNA and goal resolve through.
        questionnaire: The published question set defining the Required Brand
            DNA fields, when the caller has one.

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
