# 01 — The Postgres checkpoint tests call a stale `arun_campaign` signature

Status: needs-triage
Type: bug

## Context

Three tests in `agent-harness/tests/test_postgres.py` fail as soon as the
Postgres suite is actually run:

- `test_a_run_checkpoint_outlives_the_process_that_wrote_it`
- `test_a_run_halted_at_a_gate_is_approvable_after_a_restart`
- `test_clearing_a_campaigns_threads_removes_its_durable_state`

Each calls `arun_campaign(settings, TENANT, SLUG, stage=..., checkpointer=...)`
and gets:

    TypeError: arun_campaign() missing 3 required keyword-only arguments:
    'document_store', 'deliverable_store', and 'usage_ledger'

`arun_campaign` (`graph/runner.py:502-517`) takes `document_store`,
`deliverable_store` and `usage_ledger` as required keyword-only arguments —
dependency injection replaced whatever these tests were written against — and
the three call sites were never updated.

## Why it went unnoticed

The whole module is opt-in: it skips unless `MARKETING_OS_TEST_POSTGRES=1` is
set, and it needs Docker. `uv run pytest` reports 575 passed / 84 skipped and
stays green, so the durability guarantees these tests exist to protect —
a checkpoint outliving its process, a gate still approvable after a restart,
abandonment reaching the database rather than a dict — are currently unverified.

## Reproduce

    cd agent-harness
    MARKETING_OS_TEST_POSTGRES=1 uv run pytest tests/test_postgres.py -q
    # 3 failed, 27 passed

Confirmed present on `main` at 33c1527, independent of any in-flight branch.

## What should happen

- The three call sites pass the stores `arun_campaign` now requires, using
  whatever the module's other tests already build for the same purpose.
- The suite passes with `MARKETING_OS_TEST_POSTGRES=1`.
- Worth deciding separately whether an opt-in suite that can rot unseen should
  run in CI, since that is what let this sit.

## Acceptance criteria

- [ ] `MARKETING_OS_TEST_POSTGRES=1 uv run pytest tests/test_postgres.py` passes.
- [ ] The three tests assert the same durability behaviour they were written for,
      not a narrowed version of it.
