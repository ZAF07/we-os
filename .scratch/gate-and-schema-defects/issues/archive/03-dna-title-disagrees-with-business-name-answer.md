# The Brand DNA heading and its "Business name" field can disagree

Status: completed
Type: bug

## Parent

`.scratch/saas-foundation/issues/archive/06-questionnaire-to-brand-dna-to-gate.md` — this is a defect in that implementation.

## What's wrong

`render_brand_dna` titles the document from the `business_name` passed by the
caller ([render.py:79](../../../agent-harness/src/marketing_os/questionnaire/render.py#L79)),
which the API sources from the verified identity — the IdP's organization name —
falling back to the tenant id
([app.py:604](../../../agent-harness/src/marketing_os/entrypoints/api/app.py#L604)).
The body's `Business name` field is rendered from the owner's answer to
`q_business_name`.

These are two different values, so editing the answer changes the field and
leaves the heading stale. The Brand DNA is the document every specialist reads,
and it can state two different names for the same business.

## Reproduction

Verified over HTTP against the running service on 2026-09-02:

1. Complete onboarding with `q_business_name` = `Harbour Bikes`, under a Clerk
   organization also named `Harbour Bikes`.
2. `POST /brand-dna/answers` with `q_business_name` = `Harbour Bikes & Cargo`.
3. `GET /brand-dna` returns markdown whose heading and field disagree:

```
# Brand DNA — Harbour Bikes
...
- **Business name:** Harbour Bikes & Cargo
```

The acceptance criterion "any Brand DNA answer can be edited later" holds for the
field; the heading does not follow.

## Notes for whoever picks this up

Low severity — no gate or pipeline logic reads the heading, so nothing breaks.
It is a coherence problem in the artifact the whole system is grounded in.

The question to settle is which value is authoritative. `q_business_name` is
Required and is the business's own answer, and ADR-0018 holds that the structured
answers are the source of truth and the markdown a derived projection — which
argues for the heading rendering from the answer, with the identity name used
only as the fallback when the question is unanswered. Worth confirming that
reading before changing it, since the identity name is also what a business is
called in the IdP.

## Evidence

- [render.py:79](../../../agent-harness/src/marketing_os/questionnaire/render.py#L79) — the heading built from `business_name`.
- [app.py:604](../../../agent-harness/src/marketing_os/entrypoints/api/app.py#L604) — the identity name passed in.
- [ADR-0018](../../../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md) — structured answers as source of truth.

## Comments

**2026-09-03.** Fixed. The heading now renders from the business's own answer to
`q_business_name`, with the identity name used only as the fallback when that
question is unanswered.

That is the reading the issue proposed and asked to have confirmed: ADR-0018
holds the structured answers to be the source of truth and the markdown a derived
projection, and `q_business_name` is Required and is the business's own answer.
The IdP's organization name stays the fallback, so a business that has not yet
answered still gets a titled document rather than a bare tenant id.

`_title_for` takes the first line of a multi-line answer and treats a
whitespace-only answer as unanswered, so the heading is always a single sensible
name.

### Verification

Through the real `POST /brand-dna/answers` and `GET /brand-dna` endpoints,
reproducing this report's steps:

```
--- onboarded, identity organization "Harbour Bikes" ---
# Brand DNA — Harbour Bikes
- **Business name:** Harbour Bikes

--- after POST /brand-dna/answers editing q_business_name (200) ---
# Brand DNA — Harbour Bikes & Cargo
- **Business name:** Harbour Bikes & Cargo
```

Heading and field agree, where before the heading stayed stale.

Tests: `test_questionnaire.py::test_rendered_dna_titles_itself_from_the_business_name_answer`
and `::test_rendered_dna_falls_back_to_the_identity_name_when_unanswered`.
`test_rendered_dna_carries_every_answer_under_its_section` was asserting the old
behaviour and now asserts the corrected contract.

## Completion

- Completed: 2026-09-03
- Commit: 6636cfe
