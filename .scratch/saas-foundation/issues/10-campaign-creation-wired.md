# 10 — Campaign creation wired to the engine

Status: ready-for-agent
Type: task

## Parent

[PRD: we-OS SaaS foundation](../PRD.md) · [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)

## What to build

The new-campaign wizard stops writing to a client-side store and creates a real campaign.

The wizard collects the campaign goal: a name, one measurable business objective, a timeframe, the campaign budget (the business's media spend), the target Audience Segment chosen from the segments defined in the Brand DNA, and **all three KPI tiers** — business, marketing, and creative.

Two defects in the shipped wizard are fixed here:

- It collects only one KPI tier, but all three are Required, so every campaign it creates fails the DNA Gate.
- It asks the business owner to **pick channels**. Channel selection is the performance specialist's decision at stage 4 — the stage deliberately moved before creative in slice 01 precisely so the system makes that call. The channel questions are removed.

Campaign listing, status, and archival are wired at the same time, since they are the same resource.

End-to-end behaviour: a business owner creates a campaign from the interface, sees it appear in their campaign list with a real lifecycle status, and can start a run on it that the gate accepts.

## Acceptance criteria

- [ ] The wizard creates a real campaign owned by the signed-in tenant.
- [ ] All Required campaign-goal fields are collected, including all three KPI tiers.
- [ ] The target segment is chosen from the Audience Segments defined in the tenant's Brand DNA, not free text.
- [ ] The wizard does not ask the owner to select channels.
- [ ] A campaign created through the wizard passes the DNA Gate and can start a run.
- [ ] Incomplete input is refused with the specific missing fields named, not a generic error.
- [ ] The campaigns list shows real campaigns with lifecycle status and current stage.
- [ ] A campaign can be archived and leaves the active list.
- [ ] Campaign slugs remain unique per tenant.
- [ ] The frontend smoke suite covers the create-campaign path.
- [ ] Verified in the running app.

## Blocked by

- [06 — Questionnaire → Brand DNA → DNA Gate](06-questionnaire-to-brand-dna-to-gate.md)
