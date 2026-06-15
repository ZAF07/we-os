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

## Future capability — agent-authored frameworks (NOT active in this version)

Planned for a later version, **intentionally disabled today**: letting agents write back into this library to capture reusable frameworks they discover during real campaigns, so the knowledge base compounds over time.

In this version agents only **read** from `knowledge/` — they never write here. To activate the capability in a future version:

1. **Grant the permission** — add this line to the `permissions.allow` array in `.claude/settings.json`:
   ```
   "Write(knowledge/**)"
   ```
2. **Instruct the agents** — add guidance to the relevant subagents (e.g. `market-research`, `brand-strategy`) telling them, when they encounter a genuinely reusable, project-agnostic framework, to save it as a new `.md` file in the matching discipline folder and cite it thereafter.

Until both steps are done, this remains a read-only library and writes to `knowledge/` will prompt for approval.

