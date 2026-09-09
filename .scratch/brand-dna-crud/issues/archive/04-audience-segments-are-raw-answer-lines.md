# 04 — Campaign wizard's audience picker offers raw lines of the Brand DNA answer, not real segments

Status: completed
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

- [x] `entry_list` exists as a general `input_type`, rendered from the question set
      alone — the wizard does not special-case `q_segments`
- [x] A business can add, edit, remove and reorder audience segments in the Brand
      DNA, each with a title and a description, and the order is preserved
- [x] An answer round-trips: entries render into `dna.md` as `Title — description`
      sub-bullets and read back as the same entries, with no change to
      `markdown.py` or `render.py`
- [x] "Audience & budget" shows one selectable option per segment, displaying both
      its title and its description
- [x] The selected segment stored on the campaign goal is the title only, and
      downstream stages use it as the segment header
- [x] `audience_segments()` no longer guesses at prose: a title comes from the
      entry's title field, not from splitting a free-text sentence
- [x] Tests cover entry round-tripping in the harness and the wizard selection in
      the web app
- [x] Harness gates pass: `make check` and `make test-postgres` from `agent-harness/`
- [x] Web gates pass, run from `web/`: `pnpm lint`, `pnpm typecheck`,
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

## Completion

- Completed: 2026-09-09
- Commits:
  - `c7248fa` — Audience segments are named entries, not chopped-up prose
  - `ffd2a9a` — Address code review: share the entry-list vocabulary, cover
    remove and reorder

Verified against the running system, not just the tests:

- `entry_list` is rendered from the question set alone — `q_segments` appears
  nowhere in `web/src`, and the control takes no question-specific copy.
- The round trip was proved end to end: entries render into `dna.md` as
  `Title — description` sub-bullets and read back as the same entries, with
  `markdown.py` and `render.py` absent from the diff entirely.
- The wizard shows both halves of each segment and stores the title alone,
  which `render_field(SEGMENT_LABEL, ...)` writes as the segment header.
- `audience_segments()` takes the title from the entry's own title field;
  no prose is guessed at.
- Gates: `make check` (648 passed) and `make test-postgres` (758 passed) from
  `agent-harness/`; from `web/`, `pnpm lint`, `pnpm typecheck`,
  `pnpm test:unit` (90 passed), `pnpm format:check`, and the full Playwright
  suite (71 passed against a freshly seeded e2e stack).

### Reopened after manual testing, then closed again

The change above was archived too early. It was verified only against answers
already in entry form — every fixture and every e2e run started from freshly
seeded data — so nothing exercised the case that matters most in practice: an
answer written *before* the question collected entries.

Manual end-to-end testing on a real account found two failures, both from that
same blind spot:

1. **The Brand form shattered a prose answer.** Reading one entry per line
   turned a four-section answer into twenty-six numbered cards — headings,
   sentences and bullet fragments each posing as a segment. That is the very
   chopped-up prose this issue exists to end, moved from the campaign picker
   into the Brand form.
2. **The campaign picker offered nothing at all.** `audience_segments()` strips
   `- ` bullets but left `###` headings, so an answer written as markdown
   sections parsed to zero options and the wizard's segment step was empty.

Both sides now read an answer as the shape it actually has: one entry per
markdown heading when it has headings, one entry for unstructured prose, and
one per line only when every line is already `Title — description`. Writing
folds a description's own newlines to spaces, since one entry is one line —
otherwise a rescued description shatters again on the next save.

The "no migration" decision was read too literally the first time. It rules out
a compatibility layer; it does not license breaking answers already in the
database.

- Commits: `a88aa69` (web), `2ae112d` (harness)
- Verified against both real tenants in the running dev stack, not fixtures:
  the prose answer opens as 4 cards and offers 4 picker titles (0 before); the
  already-formatted answer stays at 2 and is unaffected. Save → re-open → save
  is stable with no drift, and the full chain form → `dna.md` → picker keeps
  all four segments.
- Gates re-run green: `make check` (650) and `make test-postgres` (760); from
  `web/` lint, typecheck, `pnpm test:unit` (95), `format:check`, and the full
  Playwright suite (71).
