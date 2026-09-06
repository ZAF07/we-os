# 03 — A billed model call is one interface, not a five-line ritual

Status: completed
Type: task

## Parent

[ADR-0020](../../../docs/adr/0020-usage-ledger-and-enforced-quota.md) · [ADR-0001](../../../docs/adr/0001-ports-and-adapters-architecture.md)

## Why

ADR-0020 makes the check-then-charge ordering load-bearing: recording without
checking first observes an overspend rather than preventing one. Today that
ordering is an open-coded pattern each billable call site must remember —
written twice, verbatim, at `graph/nodes.py:517-535` and `587-610`:

    ledger.check(tenant)  →  except QuotaExhausted → _quota_halt
    with get_usage_metadata_callback()
      await …ainvoke / .areview
      finally: _charge(…, _usage_delta(cb))
    return …, _usage_delta(cb)      # computed twice

Billing is domain logic. `graph/nodes.py` is LangGraph wiring — the adapter side.
Under ports and adapters the quota rule belongs in the core, not in the module
that happens to call it, and billing is a rule that will change and extend
(per-model rates, per-stage budgets, a soft cap that warns before it halts).

## Scope

A `billing` module in the core owning the whole sequence:

    async def billed_call[T](
        ledger: UsageLedger | None,
        state: CampaignState,
        stage: Stage,
        call: Callable[[], Awaitable[T]],
    ) -> tuple[T, dict[str, int]]

Generic over the result type, because the two callers differ — the specialist
awaits `agent.ainvoke(...)`, the reviewer `.areview(...)`. The quota check runs
before the callable, the charge in `finally`, so no caller can reorder them.

Moves with it, since all three are billing domain logic rather than graph
concerns: `_usage_delta` (`nodes.py:144`), `_charge` (`179`), `_quota_halt`
(`208`).

Stays in `nodes.py`: result shaping. `result["messages"][len(inbound):]` is a
graph concern and does not belong in the billing module.

Rejected: a private helper in `nodes.py`. It would remove the duplication but
leave the quota rule in the adapter layer, and gives billing nowhere to grow.

## Acceptance criteria

- [x] Both call sites read as one awaited call plus result shaping; neither open-codes the ordering.
- [x] `_usage_delta` is computed once per call, not twice.
- [x] The quota check provably precedes the model call, and the charge runs in `finally` on both the success and failure paths.
- [x] Quota behaviour is testable without running a graph — a test drives `billed_call` directly.
- [x] A charge still happens when the awaited call raises.
- [x] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.

## Comments

**2026-09-06.** Review candidate **03**, from the `/grill-with-docs` session.
Two call sites is a thin case for extraction on duplication grounds alone; the
case here is layering — this is a domain rule sitting in graph wiring — plus the
fact that getting the order wrong is a silent overspend rather than a visible bug.

## Completion

- Completed: 2026-09-07
- Commit: `5d3aabf` — Postgres is the only backend, and billing is a core module

`billing.py` at the top level, beside `ports.py` / `schemas.py`, owning
`billed_call` plus the three helpers that moved with it (`usage_delta`,
`billed_model`, `charge`) and the `USAGE_KEYS` constant that `nodes.py` had its
own copy of. Both call sites now read as one awaited call plus result shaping,
and `usage_delta` is computed once per call rather than twice.

Generic over the result type with a `TypeVar` rather than PEP 695 syntax:
`pyproject.toml` sets `requires-python = ">=3.11"`, and `def billed_call[T]` is
3.12+. The local venv is 3.13, so this only surfaced under `ruff`, whose target
version follows the declared floor.

**One departure from the stated scope.** `_quota_halt` stays in `nodes.py`
rather than moving with the other three. It emits a stream event through
LangGraph's `get_stream_writer` and returns a graph state update
(`route`/`halt`) — both graph concerns — so moving it would have dragged
`_emit` into the billing module or forced a circular import back into
`nodes.py`. `billed_call` raises `QuotaExhaustedError`; turning that refusal
into a halted run stays the graph's business, which reads as the cleaner seam:
billing owns the ordering, the graph owns what a refusal looks like as state.

Quota behaviour is now testable without a graph: `tests/test_billing.py` drives
`billed_call` directly — the check preceding the call, a charge on both the
raising and the cancelled paths, and the uncharged (`ledger=None`) mode.
