# Tenant-partitioned storage, and a read sandbox that serves no tenant data

[ADR-0013](0013-multi-tenant-saas-with-dual-verified-jwt.md) says tenant scoping is enforced in the storage layer, "never at individual call sites, so a forgotten `WHERE` clause cannot leak across tenants." Implementing that rule for real (saas-foundation slice 04) exposed three places where the pre-tenancy code did not honour it. All three are closed by making **the tenant part of where a document physically lives**, rather than a filter applied to a result:

- **Campaign documents were shared across every tenant.** The filesystem `DocumentStore` mapped only `dna.md` per tenant; every `campaigns/<slug>/…` path resolved to one repository-wide tree regardless of which tenant asked. Two tenants using the same slug shared a directory. Tenant documents now live under `tenants/<tenant>/{dna.md,campaigns/<slug>/…}`, so the tenant is a path segment and there is no call shape that returns another tenant's document.
- **Run traces were reachable by run id from any tenant.** Traces lived at `logs/<slug>/<run_id>.jsonl` and were located by globbing every slug for the id, so knowing a run id was sufficient to read another business's full pipeline trace. Traces are now written to `logs/<tenant>/<slug>/<run_id>.jsonl`, and every lookup — status, trace read, SSE stream, cancel, list — searches only the caller's own subtree.
- **The read sandbox served tenant data to agents.** [ADR-0005](0005-code-enforced-filesystem-sandbox.md) scoped *writes* to `campaigns/**` but deliberately let agents "read anywhere under the repo root." Once one business's Brand DNA sits on the same disk as another's, that is a cross-tenant read primitive one prompt injection away. The sandbox now refuses the whole `tenants/` subtree — for `read`, `glob` and `grep` alike — and tenant documents reach agents only through the tenant-scoped `DocumentStore`, using logical paths (`dna.md`, `campaigns/<slug>/<name>.md`) with the tenant injected from graph state. **No tenant id is ever visible to a model**, so there is no identifier for a prompt to tamper with.

## Considered options

- **Partition by tenant in the storage layer (chosen)** — costs a data migration now and makes every store call name a tenant. Buys an invariant that survives new code: the unscoped call simply does not exist, so it cannot be reached for by accident.
- **Keep the shared trees and filter at each call site** — rejected: this is exactly the shape ADR-0013 forbids. It was also demonstrably not being done — the three leaks above are all missing filters, not broken ones.
- **Give the sandbox a per-tenant root instead of denying `tenants/`** — rejected: it would keep two independent path-resolution rules for the same documents (the sandbox's and the store's), which is how they drifted apart in the first place. One reader for tenant data is the point.
- **Leave the sandbox repo-wide and rely on the prompt** — rejected for the reason ADR-0005 already gives: prompt-based restrictions are not a security boundary.

## Consequences

- **This narrows [ADR-0005](0005-code-enforced-filesystem-sandbox.md).** Its "agents may read anywhere under the repo root" now means *anywhere in the code-shipped material* — governance, templates, knowledge, guardrails. That material is the same for every tenant, which is what makes it safe to serve unscoped.
- Specialists no longer read the Brand DNA by a path naming a business. The stage brief passes `dna.md`, and the store resolves it for whichever tenant the run belongs to.
- Cross-tenant access resolves as **404, not 403**, everywhere — a foreign id is indistinguishable from one that never existed, so existence never leaks (as frozen in `contracts/openapi.yaml`).
- The tenant id is the partition key for documents *and* traces, and becomes the Postgres row-level-security key in the next slice. Changing it later is a data migration, not a refactor — which is why it is derived from the Clerk Organization (`org_id`) rather than the user id: a business may have more than one signed-in person.
- The local repository layout no longer mirrors what an operator would hand-author. `tenants/<tenant>/` is keyed by the verified tenant claim, so a directory created by hand must be named for the real Organization id to be reachable.
