# 05 — Reminder email through the Mailer port

Status: ready-for-agent
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

When a review is due, the business owner hears about it by email, once per period.

A new `Mailer` port with two adapters: Resend, selected by a mailer setting with its API key read from the environment through config, and a no-op that logs, the default. Following the web-search pattern, the real adapter is wired only when selected, so no test or local run can email a real address.

One periodic task starts with the API and ticks every review interval, inside the single engine process. A tick selects tenants whose review is due and whose reminded-at is older than the interval, sends one email each naming the Brand page, and records reminded-at. The tick is a plain function taking a clock, so tests call it directly. There is no job framework; a dedicated worker is a later decision.

The recipient is the tenant's signed-in email from the identity provider. The email says a review is due and links to the Brand page; it makes no promise the product cannot honour.

## Acceptance criteria

- [ ] With a fake clock and a fake mailer, one tick sends exactly one email per due tenant and none to tenants not due.
- [ ] A second tick within the period sends nothing; a tick after the period sends again.
- [ ] Marking reviewed before the next period means no email is sent.
- [ ] The no-op mailer sends nothing and the app starts without a Resend key.
- [ ] Selecting the Resend adapter without a key fails at startup with a clear message.
- [ ] The loop starts with the API and stops cleanly on shutdown; a tick failure is logged and does not stop the loop.
- [ ] The mailer choice and the interval are settings, documented alongside the model and web-backend settings.
- [ ] `make check` and `make test-postgres` pass; `make test-e2e` passes; a dev run with the one-minute interval and the no-op mailer logs a reminder for the test tenant.

## Blocked by

- [04 — Brand DNA review is due](04-brand-dna-review-is-due.md)
