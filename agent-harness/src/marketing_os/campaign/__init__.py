"""The campaign domain: the Stage 0 goal, its markdown projection, and its slug.

Pure domain with no I/O — where a goal is stored is the DocumentStore's business
(ADR-0014), and who may read it is the identity layer's (ADR-0013).
"""

from __future__ import annotations

from marketing_os.campaign.goal import (
    Budget,
    CampaignGoal,
    KpiTiers,
    Timeframe,
    allocate_slug,
    audience_segments,
    missing_goal_fields,
    parse_campaign_goal,
    render_campaign_goal,
)

__all__ = [
    "Budget",
    "CampaignGoal",
    "KpiTiers",
    "Timeframe",
    "allocate_slug",
    "audience_segments",
    "missing_goal_fields",
    "parse_campaign_goal",
    "render_campaign_goal",
]
