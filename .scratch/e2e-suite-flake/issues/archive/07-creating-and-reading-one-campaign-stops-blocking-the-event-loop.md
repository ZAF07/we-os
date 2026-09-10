# 07 — Creating and reading one campaign no longer blocks the engine's event loop

Status: completed
Type: task

## Parent

[04 — The e2e suite still drops a rotating spec or two under parallel load](archive/04-the-suite-still-drops-a-rotating-spec-under-parallel-load.md) · [03 — Keep the campaign list fast as a tenant's campaigns grow](archive/03-keep-the-campaign-list-fast-as-campaigns-grow.md) · [ADR-0025](../../../docs/adr/0025-one-campaign-one-person-and-a-single-worker.md)

## What to build

Issue 03 moved the campaign list's store calls off the event loop and left
the rest where they were. Creating a campaign, reading one for its
Workspace, and checking its gate still make around ten synchronous Postgres
round trips each — the slug list, the Brand DNA read, the goal write or
read, the newest version of every stage, the archive marker, the halted
stage — inside async handlers, so every other request to the engine waits
behind them. Measured under issue 04's two-worker suite: stalls of up to
0.7 s, never a failure on their own, but latency every concurrent request
pays. The engine is one process by design (ADR-0025), so threads are the
concurrency it has, and 03 already established the pattern.

Make the create, single-campaign read and gate paths non-blocking and
bounded, in this order:

1. Prefactor: describing one campaign takes pre-read data — the goal, the
   newest version per stage, the archive marker, the waiting stage — rather
   than reading inside, the way 03 fed `progress_from_latest` for the list.
   Behaviour-preserving; the single-campaign payload is byte-for-byte what
   it was, which 03's identity tests already pin the list to.
2. Move the reads (and the create's write) off the event loop, and read
   the newest version of every stage in one statement rather than one per
   stage, so a create or a Workspace read costs a bounded number of round
   trips that never stall an unrelated request.

## Acceptance criteria

- [x] A gate read is answered while a slowed campaign creation is in flight,
      (`test_a_gate_read_is_answered_while_a_slowed_create_and_read_are_in_flight`:
      the document store's `list`, `write` and `read_many`, the deliverable
      store's `latest_by_campaign` and the registry's `active_for_campaign` are
      each slowed to 0.4 s while gate reads are issued continuously; none waits
      more than 0.25 s. On the old code the test fails with a single gate read
      answered after both paths finished. The Brand DNA `exists`/`read` inside
      create run in the same thread call as the write, `_write_new_campaign`,
      so they cannot drift back onto the loop on their own.)
      rather than after it — asserted the way 03 did for the list, with the
      store's reads and the write each verified to fail the test if left on
      the loop.
- [x] The single-campaign payload and the gate report for a draft, a running,
      (`test_the_single_campaign_payload_agrees_with_the_list_across_a_mixed_portfolio`
      pins draft, running, approved, stale and archived against the list's
      status and stage progress, and the stage report against the single read;
      `test_a_campaign_waiting_on_a_person_reads_the_same_on_every_path` drives a
      real run to a gate and pins the same three; the gate answers `ok` for
      every one, archived included. `test_a_created_campaign_reads_back_exactly_as_it_was_returned`
      pins creation to the read.)
      an awaiting-approval, a stale and an archived campaign are identical
      before and after, asserted against the list path 03 already pinned.
- [x] Reading one campaign issues a number of statements that does not grow
      (`test_reading_one_campaign_costs_the_same_number_of_statements_whatever_it_has_produced`:
      **5 statements** whether one stage or all six have produced, of which
      exactly one reads `deliverable_versions`. Before: 19, six of them on
      `deliverable_versions`.)
      with the number of stages that have produced deliverables, asserted by
      a statement-counting test against the Postgres adapter.
- [x] `make check` and `make test-postgres` pass, and `make test-e2e` stays
      (`make check` 655 passed; `make test-postgres` 766 passed; `make test-e2e`
      73 passed — see issue 05 for the fourteen gate runs this change rode on.)
      green.

## Blocked by

None — can start immediately.

## Comments

### Done (2026-09-10)

Landed as `1bd2e4b`, with review fixes in `511877c`, on branch
`e2e-flake-followups`.

**What changed.** `_read_campaign` reads one campaign into a `_CampaignRecord`
— the goal and the archive marker in one `read_many`, every stage's newest
version in one `latest_by_campaign`, the live run in one registry read — and
`_require_campaign` runs it through `asyncio.to_thread`, the way issue 03 runs
`_read_portfolio`. `_describe_campaign` derives status and stages from the
record with `progress_from_latest`, the same derivation the list uses, so the
two cannot disagree. Creation validates, allocates the slug and writes in one
thread call (`_write_new_campaign`) and describes the new campaign without
reading it back: it has produced nothing, is not archived and has no run, and
the goal survives render-then-parse byte for byte (checked). Archiving writes
the marker in a thread and describes `replace(record, archived=True)`.

**Decisions taken here, not in the issue.**

- The gate path was left alone. `GET /campaigns/{slug}/gate` is a synchronous
  `def` handler, which FastAPI already runs in its threadpool, so it never sat
  on the event loop; it is the probe the concurrency test uses precisely
  because of that.
- `GET /campaigns/{slug}/stages` for a slug the tenant does not own is now a
  404, as the single read already was. It used to derive an all-pending report
  for a campaign that did not exist; nothing called it that way (the web app
  never calls `/stages`), and `test_reading_an_unknown_campaign_is_a_404_on_every_path`
  pins the new answer.
- The statement-counting and slow-store helpers moved from
  `test_campaign_list_cost.py` into `conftest.py` under public names, since the
  new cost test needed them too.

## Completion

- Completed: 2026-09-10
- Commit: 1bd2e4b, with review fixes in 511877c on branch `e2e-flake-followups`
