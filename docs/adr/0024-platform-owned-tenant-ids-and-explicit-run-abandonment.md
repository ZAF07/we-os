# Platform-owned tenant ids, and abandonment made explicit

Implementing [ADR-0014](0014-postgres-system-of-record-and-split-governance.md) for real (saas-foundation slice 05) forced four decisions the ADR left implicit. Each one is here because getting it wrong is invisible until production.

## The identity provider's id is data, not a key

Until now the tenant id **was** the Clerk Organization id (`org_3IlR…`). It named the `tenants/<tenant>/` directory, and would have named the Postgres partition, the run rows and the checkpoint threads. That welds every identifier in the platform to one IdP account: swap identity providers, re-create an organization, or migrate a business between organizations, and every key in the system is wrong with no way to fix it.

So we-OS mints its own tenant id (`ten_…`) and stores the IdP's identifier beside it:

```
tenants(tenant_id, name, external_auth_id)
```

`external_auth_id` — not `external_id` — because the column should say what kind of external id it is, leaving room for other external identifiers (billing, analytics) without ambiguity later.

A **Tenant Directory** port does the translation, once, on the way in from a verified token; a business's first authenticated request registers it. Nothing downstream sees an IdP identifier. The **passthrough** adapter, used by the filesystem layer and the CLI, reports the organization id as the tenant id — there is no table to mint an id in, the directory name *is* the tenant id, and minting one would orphan every existing directory. The split is therefore real only where there is a database to hold it, which is exactly where it matters.

## Checkpoint threads are keyed by tenant, not by slug

A LangGraph `thread_id` was the bare campaign slug. Slugs are chosen by businesses, so two tenants can both run `spring`. With a per-run ephemeral checkpointer that collision was invisible; with a **shared, durable** one it hands one business's mid-run state to another. Thread ids are now `<tenant>/<slug>` and `<tenant>/<slug>:<stage>`.

## Abandoning a run must be explicit, and it has two halves

Under the old ephemeral checkpointer, cancel-as-abandon was free: state died with the run, so the next run of a campaign necessarily began at stage 1. Durable checkpoints reverse the default — resuming is what happens unless something prevents it. Cancelling therefore now (a) releases the campaign claim and (b) **clears the campaign's checkpoint threads**, both the full-pipeline thread and every per-stage thread. Omitting (b) turns "a cancelled run starts clean" into "resume from the last checkpoint" — a change that passes review because nothing looks wrong, and which surfaces as a business's cancelled work reappearing. Reclaiming a crashed worker's run abandons it the same way, for the same reason.

Restart survival uses a **heartbeat** rather than a startup sweep. Each worker reports the runs it is executing; a starting worker resolves only runs whose heartbeat has gone stale. A sweep that resolved every `running` row on boot would work for one worker and, the moment there are two, kill a live peer's work on every deploy.

## The service does not own its own schema

Row-level security is the backstop that makes a forgotten tenant filter return nothing rather than everything, and it does not constrain superusers. The application therefore connects as an ordinary role — which also means it has no rights to create or alter tables, and cannot drop the policy that constrains it. Provisioning is a separate, explicit step (`marketing-os init-db --dsn <admin dsn> --app-role <role>`); the service checks the tables exist on boot and names that command if they do not.

RLS is applied to `documents` and not to `runs`: reclaiming runs after a worker dies is a cross-tenant maintenance sweep with no tenant in scope, so the runs queries carry an explicit `tenant_id` predicate on every tenant-facing path instead.

## Considered options

- **Keep the Clerk org id as the tenant id** — rejected: cheaper today, unmigratable later, and it spreads a vendor identifier through every table, path and thread id in the system.
- **Mint platform ids everywhere, including on the filesystem** — rejected: it would orphan every existing `tenants/<org_…>/` directory and demand a registry file to hold pairings the filesystem layer has no need for.
- **Clear checkpoints lazily, by starting each run on a fresh thread id** — rejected: it makes abandonment implicit again and leaves unbounded dead state in the checkpoint tables.
- **Resolve every `running` run on startup** — rejected: correct for one worker, destructive for more than one, which is the whole point of the shared registry.
- **Let the service run its own migrations on boot** — rejected: it requires giving the runtime the DDL rights that would let it remove its own RLS policy.

## Consequences

- Amends [ADR-0013](0013-multi-tenant-saas-with-dual-verified-jwt.md): the tenant is still derived from the verified claim, but through the Tenant Directory rather than directly from it. `TokenVerifier` now returns `VerifiedClaims` (naming the IdP organization); `VerifiedIdentity` carries the resolved `tenant_id` alongside the `organization_id` it came from.
- The one-active-run guard is keyed by `(tenant, slug)` rather than by slug alone — previously two tenants running the same slug blocked each other.
- Deploying requires one operator step before the first boot. `marketing-os init-db` is idempotent and safe to re-run.
- **Running more than one worker is now safe for the guard, but not yet complete.** Run *claims* and *statuses* are shared, so the concurrency guard holds and any worker can answer `GET /runs/{id}`. Run **traces** are still node-local JSONL files, so `GET /runs/{id}/stream` and the trace-read endpoint only return events on the worker that executed the run. Moving traces into shared storage is the remaining piece; until then, deploy one worker, or put sticky routing in front of several.
