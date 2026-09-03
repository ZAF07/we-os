# `marketing-os check` ignores the published questionnaire and passes a business the API blocks

Status: completed
Type: bug

## Parent

`.scratch/saas-foundation/issues/archive/06-questionnaire-to-brand-dna-to-gate.md` — this is a defect in that implementation.
[ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)

## What's wrong

The two entrypoints disagree about whether a business has passed the DNA Gate,
and the CLI is the more permissive one.

`check_gate` takes an optional `questionnaire` argument. Its Required Brand DNA
fields are derived from that published question set; omitted, the gate falls back
to parsing `templates/brand-dna.md`. The API passes the published set at all three
call sites ([app.py:692](../../../agent-harness/src/marketing_os/entrypoints/api/app.py#L692),
[app.py:715](../../../agent-harness/src/marketing_os/entrypoints/api/app.py#L715),
[app.py:969](../../../agent-harness/src/marketing_os/entrypoints/api/app.py#L969)).
The CLI passes it at neither:

- [cli.py:112](../../../agent-harness/src/marketing_os/entrypoints/cli.py#L112) — `marketing-os check`
- [cli.py:153](../../../agent-harness/src/marketing_os/entrypoints/cli.py#L153) — `marketing-os new-campaign`

So publishing a question set with a new Required question tightens the gate for
the API and not for the CLI. `new-campaign` is the more serious of the two: it
does not merely misreport, it **runs the pipeline** for a business whose Brand DNA
is incomplete against the published question set — which is the exact thing the
Brand DNA gate exists to prevent (`.claude/rules/brand-dna.md`).

## Reproduction

Verified against a running service and a real containerised Postgres on 2026-09-02.

1. `make db-up`, then start the API against it.
2. Publish a question set adding one Required question:
   ```
   uv run marketing-os publish-questionnaire --dsn <dsn> --file qset-v2.json
   → Published question set v2: 17 questions.
     The DNA Gate now requires 12 fields: ... Hard constraints, Seasonality
   ```
3. Take a tenant whose `dna.md` predates that question and run both paths.

**API path** — correctly blocked:
```
published version from DB: 2
gate ok: False
  DNA issue: missing Required field: 'Seasonality'
```

**CLI path** — wrongly passed:
```
$ uv run marketing-os check coast-coffee
✓ Stage 0 gate passed for tenant 'org_3IlRVjdAue93iyWDYAQYGLHcjBx', campaign 'coast-coffee'.
```

## Notes for whoever picks this up

The fallback is documented in `check_gate`'s docstring, so the *parameter* being
optional may well be deliberate — the question is whether the CLI should be
using it. Two things to settle during triage:

- The CLI builds a `FilesystemDocumentStore` directly and has no questionnaire
  store to hand; wiring one means deciding whether the CLI reaches Postgres for
  the published set, and what it should do when no DSN is configured.
- If the answer is "fall back to the template when there is no database", then
  the fallback should probably say so out loud rather than printing a bare
  green checkmark, since a passing gate is what authorises a pipeline run.

## Evidence

- [cli.py:112](../../../agent-harness/src/marketing_os/entrypoints/cli.py#L112), [cli.py:153](../../../agent-harness/src/marketing_os/entrypoints/cli.py#L153) — the two calls omitting `questionnaire`.
- [gate.py:156-186](../../../agent-harness/src/marketing_os/governance/gate.py#L156-L186) — `check_gate`'s signature and the template fallback.
- `.claude/rules/brand-dna.md` — the gate this weakens.

## Comments

**2026-09-03.** Fixed. The CLI now resolves the published question set and passes
it to `check_gate` at both call sites, so `check` and `new-campaign` enforce the
same gate the API enforces.

Decisions settled, per the "Notes for whoever picks this up":

- **The CLI does reach Postgres for the published set** when
  `MARKETING_OS_POSTGRES_DSN` is configured, through `read_published_questionnaire`.
- **With no DSN it gates against the code-shipped seed set**, not the template.
  That is the same set the service serves against an empty `questionnaires`
  table, so the two entrypoints agree in the no-database case too.
- **With a DSN configured but unreachable it refuses**, rather than falling back
  to the seed set — falling back there would re-open the exact disagreement this
  fixes. It fails in ~5s (`CONNECT_TIMEOUT_SECONDS`) with a `ConfigError` naming
  the variable, rather than the 30s hang and raw `PoolTimeout` traceback an
  earlier cut of this fix produced.
- **A passing gate is no longer a bare green checkmark.** It names the question
  set version, its Required field count, and where the set came from.

### Accepted limitation

An operator with **no DSN** gates against the seed set while an admin may have
published v2 to a database the operator is not pointed at — so the two
entrypoints can still disagree at that seam. This is disclosed rather than
hidden: the gate output says which set it enforced and that no database was
configured. Closing it properly means deciding whether the CLI may run at all
without a database, which is a product decision beyond this defect.

### Verification

Reproduced the issue's own steps against the containerised Postgres and the real
`org_3IlRVjdAue93iyWDYAQYGLHcjBx` / `coast-coffee` tenant:

```
$ uv run marketing-os publish-questionnaire --dsn <dsn> --file qset-v2.json
Published question set v2: 17 questions.
The DNA Gate now requires 12 fields: ... Hard constraints, Seasonality

$ uv run marketing-os check coast-coffee
✗ Stage 0 gate FAILED for tenant 'org_3IlRVjdAue93iyWDYAQYGLHcjBx', campaign 'coast-coffee':
    - DNA: missing Required field: 'Seasonality'          # exit 1

$ uv run marketing-os new-campaign coast-coffee
✗ Stage 0 gate FAILED ... - DNA: missing Required field: 'Seasonality'
                                                          # exit 1, pipeline did not run
```

Reverted to v1 and re-ran:

```
$ uv run marketing-os check coast-coffee
✓ Stage 0 gate passed for tenant 'org_3IlRVjdAue93iyWDYAQYGLHcjBx', campaign 'coast-coffee'.
    Gated against question set v1 (11 Required fields) — the set published to the database.
```

Tests: `test_cli.py::test_check_enforces_the_seed_question_set_not_the_template`,
`::test_check_says_which_question_set_it_gated_against`,
`::test_check_gates_against_the_published_set_when_a_dsn_is_configured`,
`::test_new_campaign_refuses_a_dna_incomplete_against_the_published_set`,
`::test_check_refuses_clearly_when_the_configured_database_is_unreachable`.

## Completion

- Completed: 2026-09-03
- Commit: 6636cfe
