# 04 — Pricing leaves the Landing

Status: ready-for-agent
Type: task

## Parent

[PRD: We-OS Landing and Pricing](../archive/PRD.md) · supersedes the Landing's pricing section from [02](archive/02-tiers-on-pricing-and-landing.md)

## What to build

Decided by the maintainer on 2026-09-09, after seeing the shipped page: the
Landing tells the story from the hero to "Why it's different" and then answers
the FAQ. The tiers live only on the Pricing page, which keeps the FAQ. So the
Landing's pricing section goes; the top bar and footer keep their "Pricing"
links, so the tiers stay one click away; the final call to action stays on
both pages.

The visitor spec drops its Landing tier assertions and its expected heading
list loses the pricing heading; it still asserts the Pricing links. The
glossary's Landing and Pricing entries follow: what it costs is no longer on
the Landing, and Pricing is the only place prices appear.

## Acceptance criteria

- [ ] With no session, the Landing shows, in order: hero, the augmented loop, how it works, your marketing department, why it's different, FAQ, final call, footer — and no tier card.
- [ ] `/pricing` is unchanged: the three tiers, the FAQ, the final call.
- [ ] "Pricing" in the top bar and the footer still reaches `/pricing`.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test:unit`, and `pnpm test` pass, and the change is checked in the running app.

## Blocked by

None.
