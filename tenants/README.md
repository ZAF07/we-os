# Tenants

Everything a business owns lives under its own directory here:

```
tenants/
  <tenant>/
    dna.md                        # the business's Brand DNA (one per tenant)
    campaigns/<slug>/goal.md      # per-campaign input
    campaigns/<slug>/*.md         # deliverables written by the pipeline
```

## What a tenant is

A **tenant is one business**, marketing itself ([ADR-0013](../docs/adr/0013-multi-tenant-saas-with-dual-verified-jwt.md)). we-OS is not an agency platform: a tenant never manages other businesses. One tenant → one Brand DNA → many campaigns.

The people a business sells to are **audience segments**, described *inside* its Brand DNA. They are never directories here.

## Where the tenant id comes from

A tenant id is **owned by the platform**, and the identity provider's own identifier for the business is data stored beside it — not the identifier itself ([ADR-0014](../docs/adr/0014-postgres-system-of-record-and-split-governance.md)). Clerk's Organization id (`org_...`) is a vendor detail: it changes if the IdP is swapped or an organization is re-created, and it has no business appearing in every document path, run row and checkpoint thread.

Which id you get depends on where documents live:

- **On Postgres** (production): the platform mints a `ten_...` id on the business's first authenticated request and records the pairing in the `tenants` table — `tenant_id`, `name`, `external_auth_id` (the Clerk org id). Everything the business owns is partitioned by `tenant_id`.
- **On the filesystem** (this directory — local development and the CLI): there is no table to mint an id in, and the directory name *is* the tenant id. The tenant directory therefore passes the organization id straight through, so a directory here is still named `org_...`. That is the pre-Postgres behaviour, kept deliberately so existing directories keep working.

In both cases the tenant comes from the verified token claim and never from a parameter. Running the CLI locally, it comes from `MARKETING_OS_TENANT_ID`, which must match the directory name here.

## This directory is not readable by agents

Specialists reach these documents only through the tenant-scoped `DocumentStore`, using logical paths (`dna.md`, `campaigns/<slug>/<name>.md`). The read sandbox refuses this whole subtree, so a specialist running for one business cannot read another's Brand DNA or deliverables even if its prompt is subverted into asking.

## The Brand DNA is human-authored

It is answered by the business from a curated questionnaire ([ADR-0018](../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)) — never drafted, scraped, or guessed by a model. Start from `templates/brand-dna.md`. The pipeline will not begin until every **Required** field is filled and no `<placeholder>` remains.
