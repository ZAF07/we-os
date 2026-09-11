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

## Comments

**2026-09-11 — plan (agent).** Branch `feat/clarifications-05-reminder-email`, worked in a scratchpad worktree.

- Settings: `mailer` from `MARKETING_OS_MAILER` (`noop` by default, or `resend`); `resend_api_key` from `MARKETING_OS_RESEND_API_KEY`; `mail_from` from `MARKETING_OS_MAIL_FROM`, the verified sender Resend requires; `app_url` from `MARKETING_OS_APP_URL`, where the web app is reached, so the email can link to the Brand page. Selecting `resend` without a key or a sender is refused when settings are built for the mailer, which is at startup.
- Port: `Mailer.send(message)`. Adapters in `adapters/mail.py`: `NoopMailer` logs what it would have sent and sends nothing; `ResendMailer` posts to Resend over an injected `httpx` client, as the Tavily backend does; `build_mailer(settings)` constructs the real one only when it is selected, following the web-search pattern.
- Recipient: the tenant row gains `contact_email`, refreshed from the verified claim on every request that carries one, so the address is the email of the person who last signed in. The tick has no request, so this is the only way it can know an address without an IdP secret on the engine (ADR-0013). A due tenant with no recorded address is skipped and logged, not marked, so it is emailed as soon as one is known. The Clerk checklist gains the step that puts `email` on the session token.
- Tick: `reminders.send_due_reminders(...)` is a plain function over the directory, the answer and questionnaire stores, the mailer, `now` and the interval. It walks every tenant, judges the review the way the API does (one shared `review_from_stores`), and for each due tenant whose `dna_reminded_at` is absent or older than the interval sends one email and records `dna_reminded_at = now`. One tenant's failure is logged and the walk continues.
- Loop: `reminders.remind_on_interval(tick, every)` ticks at once and then every review interval; a failing tick is logged and the loop goes on. The lifespan starts it as one task after the backend opens and cancels it on shutdown. No job framework (ADR-0028).
- Postgres: `ALTER TABLE tenants ADD COLUMN IF NOT EXISTS contact_email text` and `dna_reminded_at timestamptz`, picked up by the drift check. The directory gains `all()` and `mark_dna_reminded(...)` on every adapter; the passthrough one lists nothing and keeps nothing, as it does for the tier.
- Seed: the seeded tenant is written with the e2e user's email (`E2E_CLERK_USER_EMAIL`) and a cleared `dna_reminded_at`, so a reminder is logged on the first tick after every start and reset.
- Compose: the e2e stack names the `noop` mailer out loud and passes the web app's URL; the dev stack passes the four settings through from `.env`. Documented in `agent-harness/example.env`, `.env.example` and `docs/running-locally.md` beside the model and web-search settings.
- Tests: config parse; `build_mailer`; both mailers against a mock transport; the pure `reminder_due` and the email body; the tick with fake stores, a fake mailer and a hand-moved clock, through every acceptance case; the loop; startup refused for `resend` without a key, and started with `noop`; Postgres round-trips for the new columns and `all()`; the seed's email and reset; the drift columns.
