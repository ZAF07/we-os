# 0003 — Governance-as-markdown (single source of truth)

The rules, agent definitions, and QA rubrics that shape agent behaviour live as markdown under `.claude/` and `guardrails/`, and are read at runtime by the harness — the same files Claude Code uses interactively. We chose this so domain experts (not engineers) can change how the system behaves by editing prose, with no code change and no config drift between the interactive and compiled representations.

At runtime `governance/rules.py` (`load_governance`) assembles the operating principles + decision hierarchy + Customer DNA rule into every specialist's system prompt; `governance/rubric.py` (`load_rubric`) composes `guardrails/shared.md` + the stage-specific rubric for the QA judge; `agents/loader.py` parses `.claude/agents/*.md` frontmatter for each specialist's tools and body.

## Consequences

- Editing `.claude/rules/*`, `.claude/agents/*`, or `guardrails/*` changes behaviour immediately, with no redeploy.
- Both entrypoints and Claude Code stay in lock-step because they consume identical files.
- Each file has a compact hardcoded fallback if the markdown is missing, so a partial repo still runs.

## Evidence

- `agent-harness/src/marketing_os/governance/rules.py`, `governance/rubric.py`, `agents/loader.py`.
- `.claude/rules/{operating-principles,decision-hierarchy,customer-dna}.md`; `guardrails/*.md`; `.claude/agents/*.md`.
