# 03 — A billed model call is one interface, not a five-line ritual

Status: ready-for-agent
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

- [ ] Both call sites read as one awaited call plus result shaping; neither open-codes the ordering.
- [ ] `_usage_delta` is computed once per call, not twice.
- [ ] The quota check provably precedes the model call, and the charge runs in `finally` on both the success and failure paths.
- [ ] Quota behaviour is testable without running a graph — a test drives `billed_call` directly.
- [ ] A charge still happens when the awaited call raises.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all pass.

## Comments

**2026-09-06.** Review candidate **03**, from the `/grill-with-docs` session.
Two call sites is a thin case for extraction on duplication grounds alone; the
case here is layering — this is a domain rule sitting in graph wiring — plus the
fact that getting the order wrong is a silent overspend rather than a visible bug.
