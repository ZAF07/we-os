# 02 — The engine owns the tier

Status: completed
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

- [x] The tenant carries a nullable tier, and a tenant that has never set one reports none.
- [x] Setting a tier where none exists records it; reading the tenant back reports it.
- [x] Repeating the recorded tier succeeds and leaves it unchanged.
- [x] Naming a different tier is refused with 409 and a typed detail.
- [x] An unknown tier name is refused with 422.
- [x] A caller with no organization claim is refused with 401.
- [x] All three tenant directory adapters implement the tier read and write, with tests, following the existing directory tests' shape.
- [x] The backfill sets the recommended tier on a row that has none and leaves a set tier alone, proven by a test in the slow suite.
- [x] The backfill derives its default from the existing tier definition rather than repeating a tier name, and the engine's tier list is the only place the names appear on this side.
- [x] `make check` and `make test-postgres` both pass, with output reported.

## Blocked by

None - can start immediately. Runs in parallel with issue 01; they share no files.

## Completion

- Completed: 2026-09-09
- Commits:
  - `75d8bec` The engine owns the tier: a column, a backfill, and PUT /tenant/tier
  - `8cc55e2` Address code review: one set-once judgement, honest docstrings, real assertions
  - merged to main as `b6c878f` Merge: a tier is chosen before an account exists, and the platform creates the tenant

### Evidence

- **Criterion 1** — `Tenant.tier: TierName | None = None` and `VerifiedIdentity.tier` in `agent-harness/src/marketing_os/schemas.py`; `tests/test_tenant_directory.py::test_a_business_that_has_never_set_a_tier_reports_none` (adapter) and `..._over_the_api` (`GET /me` reports `null`); `tests/test_postgres.py::test_a_new_tenant_reports_no_tier`.
- **Criterion 2** — `test_setting_a_tier_where_none_exists_records_it`, `test_setting_a_tier_records_it_and_the_tenant_reads_it_back` (`PUT /tenant/tier` then `GET /me`), and `test_a_tier_is_set_once_and_read_back_by_every_path` against Postgres, where `resolve` and `get` both return the recorded tier.
- **Criterion 3** — `test_repeating_the_recorded_tier_succeeds_and_changes_nothing`, `..._over_the_api`, and the Postgres `test_repeating_the_tier_is_harmless_and_changing_it_is_refused`.
- **Criterion 4** — `TierAlreadySetError` in `errors.py` (409, type `tier_already_set`, carrying `recorded_tier` and `requested_tier`); `test_naming_a_different_tier_is_refused_with_409_and_a_typed_detail` asserts the body; the contract gains `TierAlreadySetError` and the enum value.
- **Criterion 5** — `set_tenant_tier` in `entrypoints/api/app.py` resolves the name through `tier_from_name` and raises the typed `ValidationError`; `test_an_unknown_tier_name_is_refused_with_422`.
- **Criterion 6** — `test_a_caller_with_no_organization_claim_is_refused_with_401` (a verifier that refuses the organization-less token, as the real one does in `tests/test_auth.py`) and `test_an_unauthenticated_caller_cannot_set_a_tier`; the directory records no resolution.
- **Criterion 7** — `TenantDirectory.set_tier` in `ports.py`; `PassthroughTenantDirectory.set_tier`, `InMemoryTenantDirectory.set_tier` (sharing `refuse_a_different_tier`) in `adapters/tenants.py`; `PostgresTenantDirectory.set_tier` in `adapters/postgres/tenants.py` with a conditional `UPDATE`. Tests follow the directory file's sections; the passthrough's "holds no tier" is pinned by `test_the_passthrough_directory_holds_no_tier`.
- **Criterion 8** — `tests/test_schema_drift.py::test_a_database_that_predates_tiers_is_backfilled_to_the_recommended_tier` drops the column, inserts a row, runs `ensure_schema` and reads back the recommended tier; `test_the_backfill_leaves_a_recorded_tier_and_an_unset_one_alone` proves a set tier and an unset one survive two more runs. Both are in the slow suite.
- **Criterion 9** — The backfill line in `adapters/postgres/schema.py` interpolates `RECOMMENDED_TIER`; `test_the_tier_backfill_takes_its_default_from_the_tier_definition` pins it, and `tests/test_tiers.py::test_the_tier_definition_is_the_only_place_a_tier_is_named_on_the_engine_side` scans the source tree. The same file pins the engine's names and recommended tier to `web/src/lib/tiers.ts`.
- **Criterion 10** — `make check`: ruff, ruff format, mypy (68 files) and pytest **644 passed, 110 skipped**. `make test-postgres`: **754 passed** (the slow suite included). `npm run lint` in `contracts/`: no errors. The e2e seed writes the recommended tier, and the compose stack's `tenants` rows showed it for both suite tenants.
