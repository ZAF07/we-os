# Agent Write-Back to the Knowledge Library

Agents do not write to the knowledge library. They read frameworks from it and cite
what they applied; they never add, edit, or propose entries. The library is
human-authored, and stays that way.

This covers any variation on the idea: agents saving a reusable framework they
discovered mid-campaign, agents proposing entries for admin review, agents
"learning" from completed campaigns into shared knowledge. The answer is the same
for all of them.

## Why this is out of scope

The knowledge library is the **grounding layer for every campaign the system will
ever run**. `knowledge/<discipline>/` is what each specialist reads to decide what
good looks like — positioning models for `brand-strategy`, channel playbooks for
`performance-marketing`, and so on. Every recommendation the system makes traces
back through it.

That makes it the wrong place to accept machine-authored content. A weak or subtly
wrong framework written back after one campaign doesn't stay contained to that
campaign — it becomes the standard the next campaign is measured against, and the
one after that. Errors compound in the direction the whole system points, and they
compound quietly: nothing in the output says "this recommendation rests on a
framework an agent invented last Tuesday."

This is the same principle the project already applies one layer up, to the Brand
DNA. From `.claude/rules/brand-dna.md`:

> The Brand DNA is authored by the business answering a curated questionnaire. It
> is **never drafted, scraped, or guessed by a model** — the business supplies
> facts, and we-OS supplies craft.

The knowledge library is the other half of that bargain. The business supplies the
facts; the library supplies the craft; the model supplies neither. Both inputs to a
campaign are human-authored on purpose, and an agent writing its own craft standards
breaks the symmetry that makes the guarantee meaningful.

The "propose, admin publishes" variant was considered and rejected too. It looks
safer, but it inverts the economics: review only works when the reviewer has more
context than the author, and an admin skimming a plausible-looking framework has
less context than the campaign that produced it. It manufactures review volume
without manufacturing judgement.

## What we do instead

Growing the library is human work, tracked as
`.scratch/backfill/issues/03-populate-knowledge-library.md` (`ready-for-human`).
Frameworks that prove themselves in real campaigns are absolutely worth adding —
a person adds them, deliberately.

Agents remain read-only over `knowledge/`, enforced by omission: `.claude/settings.json`
grants `Write(campaigns/**)` and nothing for `knowledge/**`, and the harness sandbox
(`agent-harness/src/marketing_os/adapters/tools/sandbox.py`) scopes writes to
`campaigns/<slug>/` while allowing repo-wide reads of knowledge and guardrails.

Note that [ADR-0014](../docs/adr/0014-postgres-system-of-record-and-split-governance.md)
moves the library into Postgres as admin-editable, versioned content. That changes
*where* a human edits it, not *who* may. This rejection survives that migration.

## Prior requests

- `.scratch/backfill/issues/archive/07-knowledge-write-back.md` — "Knowledge write-back: let agents contribute frameworks back to the library" (rejected 2026-09-02). Originally one of three candidates in "Planned extensions: approval node, Postgres persistence, knowledge write-back"; the other two were built or moved elsewhere.
- `knowledge/README.md` "Future capability — agent-authored frameworks" (2026-08 or earlier) — documented as planned-but-disabled. Superseded by this decision; that section now records the rejection instead.
