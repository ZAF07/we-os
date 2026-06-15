# Customer DNA Gate

Marketing OS produces sharp work only when grounded in real customer truth. Running without it yields generic, worthless output. Therefore:

## Gate (mandatory, before any campaign work)
No research, strategy, creative, or assets may be produced until a **complete Customer DNA** exists for the customer at `customers/<name>/dna.md`.

The orchestrator must, before delegating to any specialist:
1. Load the customer's DNA. If absent → stop and direct the operator to `templates/customer-dna.md`.
2. Verify every **Required** DNA field is present and not placeholder text (`<...>`). If any are missing → list them and stop.
3. Confirm a complete campaign goal (`campaigns/<slug>/goal.md`). If absent/incomplete → request it and stop.

Only when all three pass does the pipeline begin.

## Grounding (applies to every agent)
- Every recommendation must trace to the Customer DNA or to research findings.
- Generic, DNA-unsupported content is prohibited — no filler that could apply to any business.
- If the DNA lacks what an agent needs, the agent says so rather than inventing.

This rule governs the pipeline in `decision-hierarchy.md` and the principles in `operating-principles.md`.
