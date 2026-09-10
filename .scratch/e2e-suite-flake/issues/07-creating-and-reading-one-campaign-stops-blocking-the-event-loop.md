# 07 — Creating and reading one campaign no longer blocks the engine's event loop

Status: ready-for-agent
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

- [ ] A gate read is answered while a slowed campaign creation is in flight,
      rather than after it — asserted the way 03 did for the list, with the
      store's reads and the write each verified to fail the test if left on
      the loop.
- [ ] The single-campaign payload and the gate report for a draft, a running,
      an awaiting-approval, a stale and an archived campaign are identical
      before and after, asserted against the list path 03 already pinned.
- [ ] Reading one campaign issues a number of statements that does not grow
      with the number of stages that have produced deliverables, asserted by
      a statement-counting test against the Postgres adapter.
- [ ] `make check` and `make test-postgres` pass, and `make test-e2e` stays
      green.

## Blocked by

None — can start immediately.
