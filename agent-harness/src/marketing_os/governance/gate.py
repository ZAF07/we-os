"""Stage 0 — the Customer DNA gate.

Reproduces the orchestrator's three blocking checks:
  1. `customers/<name>/dna.md` exists.
  2. Every **Required** DNA field is present and not a `<...>` placeholder.
  3. `campaigns/<slug>/goal.md` exists with its Required fields filled.

Which fields are "Required" is read from the templates' `## Required` section, so
adding a Required field to a template automatically tightens the gate — no code
change. Fails by raising `GateError` with the exact offending fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from marketing_os.config import Settings
from marketing_os.errors import GateError

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


def validate_document(template_path: Path, doc_path: Path) -> list[str]:
    """Return a list of human-readable issues; empty means the document passes."""
    if not doc_path.is_file():
        return [f"file missing: {doc_path}"]
    labels = required_fields(template_path)
    values = field_map(doc_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    for label in labels:
        if label not in values:
            issues.append(f"missing Required field: '{label}'")
        elif _is_placeholder(values[label]):
            issues.append(f"placeholder/empty Required field: '{label}'")
    return issues


@dataclass
class GateReport:
    """Structured outcome of the Stage 0 gate."""

    customer: str
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


def check_gate(settings: Settings, customer: str, slug: str) -> GateReport:
    """Run the gate and return a report (does not raise)."""
    dna_path = settings.customers_dir / customer / "dna.md"
    goal_path = settings.campaigns_dir / slug / "goal.md"
    dna_template = settings.templates_dir / "customer-dna.md"
    goal_template = settings.templates_dir / "campaign-goal.md"

    report = GateReport(customer=customer, slug=slug)
    if not dna_path.is_file():
        report.dna_issues.append(
            f"no Customer DNA at {dna_path}. Create it: "
            f"cp templates/customer-dna.md customers/{customer}/dna.md, "
            "then fill every Required field."
        )
    else:
        report.dna_issues.extend(validate_document(dna_template, dna_path))

    if not goal_path.is_file():
        report.goal_issues.append(
            f"no campaign goal at {goal_path}. Create it: "
            f"cp templates/campaign-goal.md campaigns/{slug}/goal.md, "
            "then fill every Required field."
        )
    else:
        report.goal_issues.extend(validate_document(goal_template, goal_path))
    return report


def enforce_gate(settings: Settings, customer: str, slug: str) -> GateReport:
    """Run the gate and raise GateError if it does not pass."""
    report = check_gate(settings, customer, slug)
    if not report.ok:
        raise GateError(
            "Stage 0 gate failed — work cannot begin until these are fixed:\n  - "
            + "\n  - ".join(report.all_issues),
            missing=report.all_issues,
        )
    return report
