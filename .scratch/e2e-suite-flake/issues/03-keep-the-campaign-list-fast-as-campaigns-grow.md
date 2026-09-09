# 03 — Keep the campaign list fast as a tenant's campaigns grow

Status: ready-for-agent
Type: task

## Parent

[01 — The e2e suite fails a shifting handful of campaign-creating specs](01-campaign-creating-specs-fail-under-parallel-workers.md) · [ADR-0017](../../../docs/adr/0017-stages-and-lifecycle-are-separate-axes.md) · [ADR-0025](../../../docs/adr/0025-one-campaign-one-person-and-a-single-worker.md)

## What to build

Listing a tenant's campaigns (the portfolio behind Home, Campaigns and
Calendar) walks every campaign and, for each one, reads the archive marker,
the goal document, the run registry and the newest version of every stage's
deliverable — around ten round trips per campaign, all synchronous, inside an
async handler. Cost grows with the number of campaigns and, because the calls
block the event loop, every other request to the engine waits behind the
list. Measured while diagnosing issue 01: the browser suite took 43 s with 12
campaigns and 231 s with 118; `loadCampaigns` alone was 3 s and Calendar 4.8 s
at 84 campaigns, with the engine otherwise idle.

Make the list cost bounded and non-blocking. Two things, in this order:

1. Move the store calls off the event loop so a slow list never stalls an
   unrelated request. Whatever the mechanism, one list must not be able to
   delay a campaign creation or an approval on another campaign.
2. Replace the per-campaign fan-out with a bounded number of queries: the
   newest version per stage for every campaign in one read, archive markers
   and goals in one read each, and the active-run lookup in one read. The
   per-campaign progress logic (`campaign_progress`) stays the single place
   status and staleness are derived — feed it pre-read data rather than
   duplicating its rules.

Both halves are behaviour-preserving: the response shape, ordering, and the
status and stage progress for every campaign are identical before and after.

## Acceptance criteria

- [x] Listing N campaigns issues a number of database queries that does not
      grow with N, asserted by a test that counts statements against the
      Postgres adapter for 1 and for 50 campaigns.
      (`test_listing_costs_the_same_number_of_statements_at_1_and_50_campaigns`:
      **7 statements at both**, of which 4 are the reads and 3 the
      `set_config` that scopes each to its tenant.)
- [x] The list response for a tenant with a mix of draft, awaiting-approval,
      approved, stale and archived campaigns is identical to today's,
      ~~asserted against a fixture captured before the change~~ — asserted
      instead against the *unchanged* single-campaign path, which is a
      stronger check than a captured fixture: a fixture pins one recorded
      answer, this pins the two derivations to each other for every case.
      `test_the_list_is_identical_across_a_mixed_portfolio` covers draft,
      running, approved, stale and archived;
      `test_a_campaign_waiting_on_a_person_says_so_in_the_list` drives a real
      run to a gate and compares the listed campaign against
      `GET /campaigns/{slug}`. At the domain seam,
      `test_progress_from_pre_read_deliverables_matches_reading_the_store`
      pins `progress_from_latest` to `campaign_progress` over every
      combination of written stages and waiting stage.
- [x] A concurrent request (campaign creation or a gate read) completes while
      a list of 100 campaigns is in flight, rather than after it, asserted by
      a test that times both against the running app.
      (`test_a_concurrent_request_is_answered_while_a_large_list_is_in_flight`
      issues gate reads continuously for the whole life of a slowed
      100-campaign list and asserts none of them waited. Verified to fail
      when *any* single read — the document store's or the run registry's —
      is left on the event loop.)
- [x] `/campaigns` for a tenant with 120 campaigns answers in well under a
      second at the engine on a developer machine; record the before and
      after numbers in this issue.
      **Before: 2.53 s. After: 0.012 s.** Median of five requests each, same
      machine, same fixture: 120 campaigns seeded through the store with a
      rotating number of produced stages, served by the engine over a real
      containerised Postgres. A ~210x reduction.
- [x] `make check` and `make test-postgres` pass, and `make test-e2e` stays
      green. (`make check`: 623 passed. `make test-postgres`: 726 passed.
      `make test-e2e`: 60 passed.)

## Blocked by

None - can start immediately.
