# 04 — Campaign wizard's audience picker offers raw lines of the Brand DNA answer, not real segments

Status: ready-for-agent
Type: bug

## Symptom

Step 3 of the new-campaign wizard ("Audience & budget") asks the tenant to pick a
target audience segment. The options it shows are not segments — they are whatever
lines the business happened to type into the single free-text Brand DNA answer for
`q_segments` ("Who buys from you? Describe each distinct group, most important
first."), chopped by a dash heuristic.

The chain:

- Onboarding renders `q_segments` (`input_type: "list"`) as a plain textarea
  (`MULTILINE_TYPES` in `web/src/app/(app)/onboarding/page.tsx:22`). Nothing enforces
  one segment per line, and there is no notion of a segment having a name separate
  from its description.
- `audience_segments()` (`agent-harness/src/marketing_os/campaign/goal.py:309`) then
  splits that blob on newlines and takes the text before the first ` — ` / ` - `
  (`_SEGMENT_DETAIL_RE`) as the segment "name".
- The wizard renders each resulting string verbatim as a radio option
  (`web/src/app/(app)/campaigns/new/page.tsx:267-282`), and the chosen string is
  stored on the campaign goal and validated against the same derived list by
  `_require_known_segment()`.

Impact: no crash. The picker is unusable in practice — options are prose sentences,
a wrapped paragraph collapses to one giant "segment", a business that used commas or
bullets instead of newlines gets one option or none, and a stray dash truncates a
name mid-sentence. The `audience_segment` value that ends up on `goal.md` and feeds
every downstream stage is arbitrary text rather than a chosen thing.

## Repro

Deterministic.

1. In onboarding, answer "Who buys from you?" as prose, e.g.
   `Busy parents in the suburbs - they want quick weeknight meals, and young
   professionals who eat out a lot.`
2. Start a new campaign, advance to "Audience & budget".
3. Observe the radio options are the raw line(s) truncated at the first dash —
   here a single option reading `Busy parents in the suburbs`, with the second
   group lost entirely.

## Suspected location

- `agent-harness/src/marketing_os/questionnaire/seed.py:75-84` — `q_segments`
  definition and its `input_type: "list"`.
- `agent-harness/src/marketing_os/campaign/goal.py:41,44,309-331` —
  `_SEGMENT_FIELD`, `_SEGMENT_DETAIL_RE`, `audience_segments()`; the dash-splitting
  heuristic lives here.
- `agent-harness/src/marketing_os/entrypoints/api/app.py:1058` —
  `_require_known_segment()`, and the `GET /brand-dna/segments` route.
- `web/src/lib/engine.ts:390-393` — `getAudienceSegments()`, typed `string[]`; it
  needs to carry title + description.
- `web/src/app/(app)/campaigns/new/page.tsx:99-110,246-284` — segment loading and
  the radiogroup that renders each option.
- `web/src/app/(app)/onboarding/page.tsx:22` — `MULTILINE_TYPES`, where `list`
  currently degrades to a textarea.

## How this got here

Not an implementation defect — `audience_segments()` does exactly what it says.
The gap is upstream: `q_segments` collects a segment *list* through an
`input_type` (`list`) that renders as a plain textarea, so the answer never had
the structure the picker needs. The dash-splitting heuristic was an attempt to
recover that structure after the fact, from prose the business was never asked
to shape. Filed rather than fixed in place because the remedy changes the
question set and the shape of an answer, which is a product decision.

## Decision

An audience segment becomes a **structured entry** with a title and a
description, authored once in the Brand DNA and reused by the wizard. Settled
with the operator at filing time; the alternatives considered are in Comments.

**Storage — a line convention, not a new answer shape.** A `DnaAnswer.answer` is
a plain `str`, and `render_field()` already turns a multi-line value into one
sub-bullet per line that `walk_fields()` reads back unchanged
(`agent-harness/src/marketing_os/markdown.py:46-66`). So an entry is **one line,
`Title — description`**. Nothing about the schema, the DB, `markdown.py`, or
`render.py` changes; the em-dash split stays, but it becomes a format the UI
guarantees rather than a guess about prose.

**A generic input type.** ADR-0018 makes the question set the single artifact
driving the wizard UI, so the control must key off `input_type` and stay ignorant
of what the question is. Add `entry_list` as a new input type: a repeatable
control where each row is a short **title** and a **description**, with add,
remove and reorder. Order carries meaning — most important first — so preserve
it. `q_segments` moves from `list` to `entry_list`; the type is reusable by any
future question collecting named entries.

**Wizard side.** "Audience & budget" shows the segments as selectable cards
displaying **both** title and description, so the business can tell the groups
apart. The value stored on the campaign goal, and used as the header downstream,
is the **title** only.

**No migration.** we-OS is not live; the only existing tenant data is the
operator's own test data and will be removed rather than migrated. Do not build a
compatibility path for free-text `q_segments` answers, and do not preserve
existing `audience_segment` values.

## Acceptance criteria

- [ ] `entry_list` exists as a general `input_type`, rendered from the question set
      alone — the wizard does not special-case `q_segments`
- [ ] A business can add, edit, remove and reorder audience segments in the Brand
      DNA, each with a title and a description, and the order is preserved
- [ ] An answer round-trips: entries render into `dna.md` as `Title — description`
      sub-bullets and read back as the same entries, with no change to
      `markdown.py` or `render.py`
- [ ] "Audience & budget" shows one selectable option per segment, displaying both
      its title and its description
- [ ] The selected segment stored on the campaign goal is the title only, and
      downstream stages use it as the segment header
- [ ] `audience_segments()` no longer guesses at prose: a title comes from the
      entry's title field, not from splitting a free-text sentence
- [ ] Tests cover entry round-tripping in the harness and the wizard selection in
      the web app
- [ ] Harness gates pass: `make check` and `make test-postgres` from `agent-harness/`
- [ ] Web gates pass, run from `web/`: `pnpm lint`, `pnpm typecheck`,
      `pnpm test:unit`, `pnpm test`, `pnpm format:check`

## Comments

**2026-09-09** — Two open questions resolved with the operator at filing time;
the outcome is in `## Decision`, the alternatives rejected are here:

1. *Storage shape.* Chose the line convention (`Title — description`) over
   structured JSON in the answer. Decisive fact: `DnaAnswer.answer` is a `str`
   and `render_field`/`walk_fields` already round-trip multi-line values as
   sub-bullets, so the convention needs no schema, DB, or markdown-module change.
   JSON would have forced `render.py` to branch per `input_type` and broken the
   uniform "an answer is human-readable text" property.
2. *Migration.* None needed — the product is not live and the only existing
   tenant data is the operator's own testing, to be deleted rather than migrated.

Status moved `needs-triage` → `ready-for-agent`.
