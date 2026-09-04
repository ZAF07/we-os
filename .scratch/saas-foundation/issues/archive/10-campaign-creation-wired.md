# 10 — Campaign creation wired to the engine

Status: completed
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

- [x] The wizard creates a real campaign owned by the signed-in tenant.
- [x] All Required campaign-goal fields are collected, including all three KPI tiers.
- [x] The target segment is chosen from the Audience Segments defined in the tenant's Brand DNA, not free text.
- [x] The wizard does not ask the owner to select channels.
- [x] A campaign created through the wizard passes the DNA Gate and can start a run.
- [x] Incomplete input is refused with the specific missing fields named, not a generic error.
- [x] The campaigns list shows real campaigns with lifecycle status and current stage.
- [x] A campaign can be archived and leaves the active list.
- [x] Campaign slugs remain unique per tenant.
- [x] The frontend smoke suite covers the create-campaign path.
- [x] Verified in the running app. _(Engine boundary only — see Completion.)_

## Blocked by

- [06 — Questionnaire → Brand DNA → DNA Gate](archive/06-questionnaire-to-brand-dna-to-gate.md)

## Completion

- Completed: 2026-09-03
- Commits: `cf21c07` (implementation), `6636cfe` (gate-and-schema fixes)
- Commit: cf21c070986265bb3774e87e49dc11399202216b

### Evidence per criterion

All engine behaviour was exercised against a real running engine
(`uvicorn` on the real repo root) as the real tenant
`org_3IlRVjdAue93iyWDYAQYGLHcjBx`, plus 40 automated tests
(`tests/test_campaigns_api.py`, `tests/test_campaign_goal.py`).

1. **Real campaign, signed-in tenant** — `POST /campaigns` derives the tenant
   from `identity.tenant_id`, never the body;
   `test_a_caller_supplied_tenant_in_the_body_is_ignored` proves a smuggled
   `tenant` field is ignored (ADR-0013).
2. **All Required fields incl. three KPI tiers** — `missing_goal_fields`
   (`campaign/goal.py`) checks all nine; wizard step 2 collects business,
   marketing and creative.
3. **Segment from the Brand DNA, not free text** — wizard renders a
   `role="radiogroup"` fed by `GET /brand-dna/segments`; the engine independently
   refuses an unknown segment
   (`test_create_campaign_rejects_a_segment_the_brand_dna_does_not_name`). Live:
   `"Invented people"` → 422 naming the one segment the DNA defines.
4. **No channel question** — `CHANNELS`, the Channels step and the `channels`
   field are gone; only explanatory copy remains (ADR-0016).
5. **Passes the gate, starts a run** — live: `GET /campaigns/verify-push/gate`
   → `{"ok":true,"issues":[]}`; `POST .../run` → `202` with a run id.
6. **Missing fields named** — live: omitting the creative KPI →
   `422 "The campaign goal is incomplete. Missing: kpis.creative."` Every
   missing field is listed, not just the first.
7. **List shows real campaigns** — live listing returned all seven campaigns
   with `status` and `stage_progress`, including hand-authored ones (the list
   reads the document store, not a registry).
8. **Archive leaves the active list** — live: archived campaign absent from
   `GET /campaigns` but still readable at `GET /campaigns/{slug}` as
   `archived`.
9. **Slugs unique per tenant** — live: the same name twice →
   `verify-push`, `verify-push-2`.
10. **Smoke suite covers create-campaign** — new test in
    `web/tests/smoke.spec.ts`, asserting the created campaign's page renders
    (not only its URL).
11. **Verified in the running app — engine boundary only.** Every item above
    was driven against a live engine. The **browser UI was not** — `pnpm test`
    needs Clerk credentials and a seeded engine that a clean checkout does not
    have. The Playwright specs are written but **unexecuted**. Tracked as
    [13](../13-frontend-suite-cannot-run-without-credentials.md); slices 11 and
    12 carry the same criterion and were annotated with the same caveat.

### Notes for whoever picks up slice 11

`web/src/app/campaigns/[slug]/page.tsx` carries an **interim** page:
`CampaignGoalDocument`, shown for any real slug, alongside the old fixture
workspace still shown for `campaignRows` slugs. It exists only so a newly
created campaign does not land on "Campaign not found". Slice 11 should delete
both branches. See that issue's Comments.

### Deviations from the issue as written

- **Frozen contract amended, deliberately.** `GET /brand-dna/segments` was added
  and declared; `objective` added to `CampaignSummary`; `offer`/`constraints`
  declared on `CampaignCreate`/`Campaign`; the always-null `created_at`/
  `updated_at` were dropped rather than shipped as permanently-null fields.
  Spectral lints clean.
- **A tenancy test was corrected.** `test_a_deliverable_name_cannot_traverse_out_of_the_campaign`
  listed a bare `..`, which an HTTP client resolves away before sending — it only
  passed because no `/campaigns/{slug}` route existed. Replaced with encoded
  traversals that actually reach the server.
- **`contracts/npm test` (Prism happy-path) fails** — but identically on the
  unmodified spec, so it is a pre-existing local issue, not this change. Prism
  serves the modified spec correctly.

### Gates

`ruff check`, `ruff format --check`, `mypy src`, `pytest` (469 passed, 68
skipped); `tsc --noEmit`, `eslint`, `prettier --check`, `next build`; Spectral
contract lint — all pass. Playwright: not run (see criterion 11).
