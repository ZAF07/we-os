# 02 — The engine owns the tier

Status: ready-for-agent
Type: task

## Parent

[PRD: A tier before an account](../PRD.md) · [ADR-0027](../../../docs/adr/0027-the-platform-creates-the-tenant-and-owns-the-tier.md) · [ADR-0013](../../../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)

## What to build

A business's **Tier** becomes the platform's own record, stored on its tenant row, so a rule about a tier can be written without asking the identity provider.

The tenant gains a nullable tier column, added by the schema module beside the existing guarded migrations. A guarded update backfills rows that have no tier to the **recommended** tier — the one the tier definition already marks as the default for a business unsure which to pick, not a name repeated here. Nothing yet distinguishes the tiers, so a default costs nothing and is corrected when billing arrives. A row that already carries a tier is left alone.

The engine learns the three tier names and nothing else — no prices, no credit amounts, which stay in the web app's tier module. The names live in one literal, and that literal and the web module each carry a comment naming the other, so whoever renames one finds the other.

A narrow endpoint, `PUT /tenant/tier`, takes the tier in the body. The tenant comes from the verified claim and never from the body (ADR-0013). Its semantics are set-once:

- Setting a tier on a business that has none succeeds.
- Repeating the tier already recorded succeeds and changes nothing — the welcome flow's retry depends on this.
- Naming a different tier than the one recorded is refused with **409** and a typed detail, alongside the engine's existing typed failures. A tier change is a billing event; when billing lands it arrives on a webhook, not on a call the account holder makes about their own subscription.
- An unknown tier name is refused with **422**, so the column holds one of three values.
- A caller whose token carries no organization claim is refused with **401**, as every tenant-scoped endpoint already is.

The tenant directory port grows the tier read and write, and all three adapters implement it: Postgres, in-memory, and the passthrough adapter used by the filesystem layer, which holds no tier because it has no table to hold one in.

The tenant row is still minted implicitly by the directory's resolve, on the first authenticated call. There is no create-tenant endpoint; this is simply the first such call a new business will make.

Nothing calls this endpoint yet. It ships complete and unused, and issue 03 wires it up.

## Acceptance criteria

- [ ] The tenant carries a nullable tier, and a tenant that has never set one reports none.
- [ ] Setting a tier where none exists records it; reading the tenant back reports it.
- [ ] Repeating the recorded tier succeeds and leaves it unchanged.
- [ ] Naming a different tier is refused with 409 and a typed detail.
- [ ] An unknown tier name is refused with 422.
- [ ] A caller with no organization claim is refused with 401.
- [ ] All three tenant directory adapters implement the tier read and write, with tests, following the existing directory tests' shape.
- [ ] The backfill sets the recommended tier on a row that has none and leaves a set tier alone, proven by a test in the slow suite.
- [ ] The backfill derives its default from the existing tier definition rather than repeating a tier name, and the engine's tier list is the only place the names appear on this side.
- [ ] `make check` and `make test-postgres` both pass, with output reported.

## Blocked by

None - can start immediately. Runs in parallel with issue 01; they share no files.
