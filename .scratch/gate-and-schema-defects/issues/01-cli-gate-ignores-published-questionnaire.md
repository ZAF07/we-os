# `marketing-os check` ignores the published questionnaire and passes a business the API blocks

Status: needs-triage
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
