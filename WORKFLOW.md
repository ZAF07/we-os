# My Workflow Cheat Sheet

My personal reference for how to run a task through Claude Code in this repo. Everything routes through the local issue tracker in `.scratch/` so both of us stay in sync across sessions.

**The one rule:** every task — feature, bug, or improvement — gets an issue file in `.scratch/<feature>/issues/` *before* any code changes. That file is the memory between sessions.

---

## Every session

**Start** → type `/triage` ("show me what needs attention")
Re-orients me and you on what's in flight. This replaces "where were we?"

**End, work finished** → `/post-implement`, then commit the `.scratch/` change
Commit message: `updated tasks status`

**End, work half-done** → tell me to add a status note under `## Comments` in the active issue
Captures where things stand + what's next, so the next session picks up cold.

---

## New feature

| Step | Command | What it does |
|---|---|---|
| 1 | `/grill-with-docs` | Interviews me to sharpen the idea; writes ADRs + updates `CONTEXT.md`. *(skip for small, obvious work)* |
| 2 | `/to-prd` | Turns the conversation into `.scratch/<feature>/PRD.md` |
| 3 | `/to-issues` | Splits the PRD into small end-to-end slices with dependencies |
| 4 | `/implement <issue path>` | Builds one issue, test-first, on a branch; runs quality gates + `/code-review` |
| 5 | `/verify` (or `/run`) | Runs the actual app to confirm it *works*, not just that tests pass |
| 6 | `/post-implement` | Verifies each acceptance criterion, marks `completed`, archives the issue |

Small feature? Skip 1–2, write one issue, go to step 4. **Never skip the issue file, and never skip step 5** — passing tests aren't proof the app works.

---

## Bug / debugging

| Step | Command | What it does |
|---|---|---|
| 1 | `/file-bug <what's broken>` | Creates the issue file in `.scratch/<feature>/issues/` with the right number + `Status:` |
| 2 | `/diagnosing-bugs` | Builds a tight pass/fail repro *before* touching code |
| 3 | `/tdd` | Fix test-first — the repro becomes the failing test |
| 4 | `/verify` | Confirm the fix holds in the running system, not just in the test |
| 5 | `/code-review` → `/post-implement` | Review, then close; record the confirmed hypothesis in the issue |

### Filing the bug — `/file-bug`

`/file-bug` handles step 1 for either of us: it picks/reuses the feature folder, assigns the next issue number, sets `Status:` (defaults to `needs-triage`), and writes the symptom + repro + acceptance criteria.

- **You**: type `/file-bug web_fetch crashes the run on a dead URL`
- **Me**: I file it when the *running system* surfaces a defect, then tell you the path.

**What is (and isn't) a bug:** file bugs that arise **after** implementation, when the system is running and crashes or logs an error. A defect in code being written *right now* — a broken function in the current diff, a test I just made fail — is **not** filed; it gets fixed in place as part of finishing that work.

The file grows a `## Root cause` and a tighter repro during `/diagnosing-bugs`. See `.scratch/web-tool-hardening/issues/01-recover-web-tool-navigation-errors.md` for a fully worked-out bug file.

---

## Improve / refactor existing code

| Situation | Command |
|---|---|
| Clean up a recent diff | `/simplify` |
| Structural / architecture change | `/improve-codebase-architecture` (uses `/codebase-design` vocabulary) |

Then funnel the scoped work into an issue and follow **New feature** steps 4–6 (including `/verify`). Refactors get issues too, and get verified too — a refactor that passes tests but changes behaviour is a bug.

---

## "Done" checklist (must all be true)

1. Change **verified in the running app** (`/verify` or `/run`) — not just green tests.
2. Quality gates pass:
   ```
   uv run ruff check .
   uv run ruff format
   uv run mypy src
   uv run pytest
   ```
3. New behaviour has tests; a bug fix has a test that was red before, green after.
4. The issue's acceptance criteria are checked off with evidence.

---

## Handy extras

- `/handoff <what next session will do>` — full handoff doc (heavier than a `## Comments` note; use for big context switches)
- `/find-skills` — search for a skill when I don't have one for the job
- `docs/agents/issue-tracker.md` — the tracker conventions in full
- `CONTEXT.md` + `docs/adr/` — domain vocabulary and past decisions

---

*The router version of this (for Claude to follow automatically) lives in `CLAUDE.md` under "Development workflow". This file is the human-readable copy for me.*
