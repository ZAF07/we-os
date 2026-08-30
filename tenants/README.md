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

- **Running the SaaS engine**: the tenant is derived from the verified token claim — the Clerk Organization id (`org_...`). No endpoint accepts it as a parameter; the directory name must match the claim.
- **Running the CLI locally**: the tenant comes from `MARKETING_OS_TENANT_ID`, which must match the directory name here.

## This directory is not readable by agents

Specialists reach these documents only through the tenant-scoped `DocumentStore`, using logical paths (`dna.md`, `campaigns/<slug>/<name>.md`). The read sandbox refuses this whole subtree, so a specialist running for one business cannot read another's Brand DNA or deliverables even if its prompt is subverted into asking.

## The Brand DNA is human-authored

It is answered by the business from a curated questionnaire ([ADR-0018](../docs/adr/0018-human-authored-dna-from-a-curated-questionnaire.md)) — never drafted, scraped, or guessed by a model. Start from `templates/brand-dna.md`. The pipeline will not begin until every **Required** field is filled and no `<placeholder>` remains.
