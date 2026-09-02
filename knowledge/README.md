# Knowledge Library

The central, shared domain knowledge for Marketing OS. Agents and skills read from here instead of carrying expertise inline, so frameworks stay reusable and in one place.

## How it is organized
Knowledge is split by discipline, each consumed by the matching agent:

| Directory | Read by | Holds |
|---|---|---|
| `research/` | `market-research` | Audience, competitor, market, trend, segmentation methods |
| `brand/` | `brand-strategy` | Positioning, messaging, voice, value-proposition frameworks |
| `creative/` | `creative-director`, `creative-asset-prompt` | Concepting, brief standards, prompt/format specs |
| `performance/` | `performance-marketing` | Channel playbooks, KPI models, budgeting, optimization |
| `frameworks/` | all | Cross-cutting marketing & advertising frameworks |

## Convention
- Add each framework or methodology as its own `.md` file inside the relevant discipline directory (e.g. `knowledge/brand/positioning-statement.md`).
- Agents should **cite which file/framework** they applied for each recommendation.
- Keep general, cross-discipline frameworks in `frameworks/`; put discipline-specific ones in their own folder.

<!-- TODO: fill each discipline directory with your expert domain knowledge. -->

## Agents never write here (decided)

Agents **read** from this library and cite what they applied. They never write to
it — not directly, and not as proposals for an admin to publish. The library is
human-authored.

An earlier version of this file described agent write-back as a planned future
capability and gave a recipe for enabling it. That capability was considered and
**rejected** on 2026-09-02. This library grounds every campaign the system runs, so
machine-authored entries would compound errors in the direction the whole system
points — the same reason the Brand DNA is human-authored (`.claude/rules/brand-dna.md`).
The full reasoning lives in [`.out-of-scope/agent-knowledge-write-back.md`](../.out-of-scope/agent-knowledge-write-back.md).

Growing this library is deliberate human work — see
`.scratch/backfill/issues/03-populate-knowledge-library.md`.
