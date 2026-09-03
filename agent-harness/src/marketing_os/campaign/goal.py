"""The campaign goal: its structured shape, its markdown projection, and its slug.

A campaign goal is the Stage 0 input the whole pipeline rests on. It states one
measurable business objective, when the campaign runs, what the business will
spend, which audience segment it targets, and all three KPI tiers — because a
campaign without all three has no definition of success (the operating
principles).

As with the Brand DNA (ADR-0018), the structured value is the source of truth and
the markdown is the derived projection. The projection targets exactly the shape
of ``templates/campaign-goal.md`` — ``- **<label>:** <value>`` lines under
``## Required`` — because that template is what the gate reads its Required field
labels from, so a rendered goal and a hand-authored one are checked identically.

The goal never names the business: a tenant is one business, so which business a
campaign belongs to is already known (ADR-0013).

Channels are deliberately absent. Channel selection belongs to the performance
specialist at stage 4, which the pipeline places before creative precisely so the
system makes that call rather than the business owner (ADR-0016).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

OBJECTIVE_LABEL = "Primary business objective"
TIMEFRAME_LABEL = "Timeframe"
BUDGET_LABEL = "Campaign budget"
SEGMENT_LABEL = "Target segment for this campaign"
BUSINESS_KPI_LABEL = "Business KPI"
MARKETING_KPI_LABEL = "Marketing KPI"
CREATIVE_KPI_LABEL = "Creative KPI"
OFFER_LABEL = "Offer / promotion"
CONSTRAINTS_LABEL = "Campaign-specific constraints"

_SEGMENT_FIELD = "Primary segment(s)"
_FIELD_RE = re.compile(r"^\s*-\s*\*\*(.+?):\*\*\s*(.*)$")
_TIMEFRAME_RE = re.compile(r"^\s*(\S+)\s*→\s*(\S+)\s*$")
_BUDGET_RE = re.compile(r"^\s*([\d,.]+)\s+([A-Za-z]{3})\s*$")
_SEGMENT_DETAIL_RE = re.compile(r"\s+[—–-]\s+")
_FALLBACK_SLUG = "campaign"


class Timeframe(BaseModel):
    """When a campaign runs.

    Attributes:
        start_date: The first day, as an ISO-8601 date.
        end_date: The last day, as an ISO-8601 date.
    """

    start_date: str = ""
    end_date: str = ""


class Budget(BaseModel):
    """The media spend available to a campaign.

    Attributes:
        amount: The spend available.
        currency: The ISO 4217 currency code.
    """

    amount: float = 0
    currency: str = ""


class KpiTiers(BaseModel):
    """The three KPI tiers every campaign defines.

    Attributes:
        business: The revenue, leads, bookings or retention target.
        marketing: The CTR, CPC, CPM or conversion-rate target.
        creative: The hook-rate, watch-time or engagement target.
    """

    business: str = ""
    marketing: str = ""
    creative: str = ""


class CampaignGoal(BaseModel):
    """A campaign's Stage 0 goal, the input the pipeline is gated on.

    Attributes:
        name: The campaign's display name.
        objective: One measurable business objective.
        timeframe: When the campaign runs.
        budget: The media spend available to it.
        audience_segment: The Brand DNA segment this campaign targets.
        kpis: All three KPI tiers.
        offer: The promotion being run, if any.
        constraints: Anything unique to this campaign beyond the DNA constraints.
    """

    name: str = ""
    objective: str = ""
    timeframe: Timeframe = Field(default_factory=Timeframe)
    budget: Budget = Field(default_factory=Budget)
    audience_segment: str = ""
    kpis: KpiTiers = Field(default_factory=KpiTiers)
    offer: str = ""
    constraints: str = ""


def _format_timeframe(timeframe: Timeframe) -> str:
    """Render a timeframe as the template's ``start → end`` value.

    Args:
        timeframe: The campaign's timeframe.

    Returns:
        The value text, empty when either end is unset so the gate reads the
        field as unfilled rather than as a stray arrow.
    """
    if not timeframe.start_date.strip() or not timeframe.end_date.strip():
        return ""
    return f"{timeframe.start_date.strip()} → {timeframe.end_date.strip()}"


def _format_budget(budget: Budget) -> str:
    """Render a budget as an amount and its currency code.

    Args:
        budget: The campaign's budget.

    Returns:
        The value text, empty when no currency is set.
    """
    if not budget.currency.strip():
        return ""
    amount = f"{budget.amount:,.2f}".rstrip("0").rstrip(".")
    return f"{amount} {budget.currency.strip().upper()}"


def _parse_timeframe(value: str) -> Timeframe:
    """Read a ``start → end`` value back into a timeframe.

    Args:
        value: The rendered field value.

    Returns:
        The timeframe, empty when the value is not in that shape.
    """
    match = _TIMEFRAME_RE.match(value)
    if match is None:
        return Timeframe()
    return Timeframe(start_date=match.group(1), end_date=match.group(2))


def _parse_budget(value: str) -> Budget:
    """Read an amount-and-currency value back into a budget.

    Args:
        value: The rendered field value.

    Returns:
        The budget, empty when the value is not in that shape.
    """
    match = _BUDGET_RE.match(value)
    if match is None:
        return Budget()
    return Budget(amount=float(match.group(1).replace(",", "")), currency=match.group(2).upper())


def render_campaign_goal(goal: CampaignGoal) -> str:
    """Render a campaign goal as the canonical ``goal.md`` the gate reads.

    Optional fields are omitted when blank rather than written as empty labels,
    so the document never carries a placeholder the gate would have to
    special-case.

    Args:
        goal: The structured goal to project.

    Returns:
        The campaign-goal markdown, ready to write to ``campaigns/<slug>/goal.md``.
    """
    lines = [
        f"# Campaign Goal — {goal.name}",
        "",
        "> Authored by the business through we-OS. The structured goal is the "
        "source of truth; this file is its canonical projection, and is what "
        "the specialists read.",
        "",
        "## Required",
        "",
        f"- **{OBJECTIVE_LABEL}:** {goal.objective}",
        f"- **{TIMEFRAME_LABEL}:** {_format_timeframe(goal.timeframe)}",
        f"- **{BUDGET_LABEL}:** {_format_budget(goal.budget)}",
        f"- **{SEGMENT_LABEL}:** {goal.audience_segment}",
        "",
        "### Success metrics (define all three tiers)",
        "",
        f"- **{BUSINESS_KPI_LABEL}:** {goal.kpis.business}",
        f"- **{MARKETING_KPI_LABEL}:** {goal.kpis.marketing}",
        f"- **{CREATIVE_KPI_LABEL}:** {goal.kpis.creative}",
    ]
    optional = [
        (OFFER_LABEL, goal.offer),
        (CONSTRAINTS_LABEL, goal.constraints),
    ]
    written = [(label, value) for label, value in optional if value.strip()]
    if written:
        lines.extend(["", "## Optional", ""])
        lines.extend(f"- **{label}:** {value.strip()}" for label, value in written)
    return "\n".join(lines).strip() + "\n"


def parse_campaign_goal(markdown: str) -> CampaignGoal:
    """Read a rendered ``goal.md`` back into its structured goal.

    The inverse of :func:`render_campaign_goal`, so the interface can show a
    campaign's goal fields without a second store holding them.

    Args:
        markdown: The campaign-goal document text.

    Returns:
        The structured goal; any field the document does not carry is empty.
    """
    values: dict[str, str] = {}
    for line in markdown.splitlines():
        match = _FIELD_RE.match(line)
        if match:
            values[match.group(1).strip()] = match.group(2).strip()

    title = next(
        (
            line.removeprefix("# Campaign Goal —").strip()
            for line in markdown.splitlines()
            if line.startswith("# Campaign Goal —")
        ),
        "",
    )
    return CampaignGoal(
        name=title,
        objective=values.get(OBJECTIVE_LABEL, ""),
        timeframe=_parse_timeframe(values.get(TIMEFRAME_LABEL, "")),
        budget=_parse_budget(values.get(BUDGET_LABEL, "")),
        audience_segment=values.get(SEGMENT_LABEL, ""),
        kpis=KpiTiers(
            business=values.get(BUSINESS_KPI_LABEL, ""),
            marketing=values.get(MARKETING_KPI_LABEL, ""),
            creative=values.get(CREATIVE_KPI_LABEL, ""),
        ),
        offer=values.get(OFFER_LABEL, ""),
        constraints=values.get(CONSTRAINTS_LABEL, ""),
    )


def missing_goal_fields(goal: CampaignGoal) -> list[str]:
    """Name every Required goal field the business has not filled.

    Every missing field is reported, not just the first, so the interface can
    refuse incomplete input by naming exactly what is absent rather than with a
    generic error.

    Args:
        goal: The goal to check.

    Returns:
        The missing fields' names, in the order the goal asks for them; empty
        when the goal is complete.
    """
    missing: list[str] = []
    if not goal.name.strip():
        missing.append("name")
    if not goal.objective.strip():
        missing.append("objective")
    if not goal.timeframe.start_date.strip():
        missing.append("timeframe.start_date")
    if not goal.timeframe.end_date.strip():
        missing.append("timeframe.end_date")
    if goal.budget.amount <= 0:
        missing.append("budget.amount")
    if not goal.budget.currency.strip():
        missing.append("budget.currency")
    if not goal.audience_segment.strip():
        missing.append("audience_segment")
    missing.extend(
        f"kpis.{tier}"
        for tier in ("business", "marketing", "creative")
        if not getattr(goal.kpis, tier).strip()
    )
    return missing


def allocate_slug(name: str, *, taken: list[str]) -> str:
    """Turn a campaign name into a slug unique within the tenant.

    Args:
        name: The campaign's display name.
        taken: The slugs the tenant already uses.

    Returns:
        A kebab-case slug, suffixed with a counter when the name collides.
    """
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or _FALLBACK_SLUG
    slug = base
    counter = 2
    while slug in taken:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def audience_segments(brand_dna: str) -> list[str]:
    """Read the audience segments a campaign may target from the Brand DNA.

    A campaign targets one of the segments the business described, never free
    text, so the interface offers exactly what the DNA names. Each segment is
    written as a name optionally followed by a dash and its detail; only the
    name identifies the segment.

    Args:
        brand_dna: The tenant's Brand DNA markdown.

    Returns:
        The segment names, in the order the business listed them; empty when the
        DNA names none.
    """
    collecting = False
    names: list[str] = []
    for line in brand_dna.splitlines():
        match = _FIELD_RE.match(line)
        if match:
            collecting = match.group(1).strip() == _SEGMENT_FIELD
            if collecting and match.group(2).strip():
                names.append(match.group(2))
            continue
        if line.lstrip().startswith("#"):
            collecting = False
        elif collecting and line.strip():
            names.append(line.strip())
    return [
        name
        for name in (
            _SEGMENT_DETAIL_RE.split(raw.strip().lstrip("-*").strip())[0].strip() for raw in names
        )
        if name
    ]
