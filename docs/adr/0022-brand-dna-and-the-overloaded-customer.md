# "Customer DNA" becomes "Brand DNA", and "customer" gets exactly one meaning

The term *Customer DNA* was carrying an agency framing the product does not have. It reads as "the DNA of a customer we serve", and the `customers/<name>/dna.md` layout it implies — a collection of businesses under one operator — only makes sense for an agency. we-OS serves one business per tenant ([ADR-0013](0013-multi-tenant-saas-with-dual-verified-jwt.md)).

Worse, *customer* was doing three jobs at once: the platform's user, the business being profiled, and the people that business sells to. The document is renamed **Brand DNA**, aligning the engine with the frontend, which already ships a Brand screen rendering exactly these sections. **Customer** is now reserved for one meaning only: the people the tenant's business sells to, described as **audience segments** inside the Brand DNA.

## Considered options

- **Business DNA** — arguably more accurate to the content, which carries price point, geography, languages and budget alongside brand and audience. Rejected in favour of aligning engine and UI vocabulary on the word operators already see.
- **Keep "Customer DNA"** — rejected: zero churn, but it preserves both the agency framing and the three-way overload that produced this correction.

## Consequences

- The rename lands in two passes. **Now:** the glossary, the ADRs, the governance markdown, the templates, the guardrails and the operator docs — the vocabulary agents load every session, which must be correct immediately. `.claude/rules/customer-dna.md` and `templates/customer-dna.md` are renamed to `brand-dna.md`, with the handful of code references that resolve those filenames updated alongside them.
- **Later, as an implementation issue:** roughly 200 references across `agent-harness/src` and its tests, the removal of the `customer` parameter, and the collapse of `customers/<name>/` into a tenant-owned singleton. That is a behavioural refactor, not a rename, and the Postgres migration ([ADR-0014](0014-postgres-system-of-record-and-split-governance.md)) subsumes the directory layout entirely — doing it before that migration would be churn the migration redoes.
- ADRs 0001–0012 are left as written. They are dated records that were accurate when made; the glossary, not the ADR history, is the authority on current vocabulary.
