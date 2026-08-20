# Brand DNA Gate

we-OS produces sharp work only when grounded in real truth about the business and the customers it sells to. Running without it yields generic, worthless output. Therefore:

## Gate (mandatory, before any campaign work)
No research, strategy, creative, or assets may be produced until a **complete Brand DNA** exists for the business at `customers/<name>/dna.md`.

The orchestrator must, before delegating to any specialist:
1. Load the business's Brand DNA. If absent → stop and direct the operator to `templates/brand-dna.md`.
2. Verify every **Required** DNA field is present and not placeholder text (`<...>`). If any are missing → list them and stop.
3. Confirm a complete campaign goal (`campaigns/<slug>/goal.md`). If absent/incomplete → request it and stop.

Only when all three pass does the pipeline begin.

## Grounding (applies to every agent)
- Every recommendation must trace to the Brand DNA or to research findings.
- Generic, DNA-unsupported content is prohibited — no filler that could apply to any business.
- If the DNA lacks what an agent needs, the agent says so rather than inventing.

## Vocabulary (non-negotiable)
- The **business** is the tenant — the company we-OS is marketing. we-OS is not an agency platform; a tenant markets itself and never manages other businesses.
- A **customer** is a person or organization *the business sells to*, described in the Brand DNA as an **audience segment**. Never use "customer" for the business, the tenant, or the platform's user.
- The Brand DNA is authored by the business answering a curated questionnaire. It is **never drafted, scraped, or guessed by a model** — the business supplies facts, and we-OS supplies craft.

This rule governs the pipeline in `decision-hierarchy.md` and the principles in `operating-principles.md`.
