# 05 — Reminder email through the Mailer port

Status: completed
Type: task

## Parent

[PRD: Clarifications](../../PRD.md) · [ADR-0028](../../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

When a review is due, the business owner hears about it by email, once per period.

A new `Mailer` port with two adapters: Resend, selected by a mailer setting with its API key read from the environment through config, and a no-op that logs, the default. Following the web-search pattern, the real adapter is wired only when selected, so no test or local run can email a real address.

One periodic task starts with the API and ticks every review interval, inside the single engine process. A tick selects tenants whose review is due and whose reminded-at is older than the interval, sends one email each naming the Brand page, and records reminded-at. The tick is a plain function taking a clock, so tests call it directly. There is no job framework; a dedicated worker is a later decision.

The recipient is the tenant's signed-in email from the identity provider. The email says a review is due and links to the Brand page; it makes no promise the product cannot honour.

## Acceptance criteria

- [x] With a fake clock and a fake mailer, one tick sends exactly one email per due tenant and none to tenants not due.
- [x] A second tick within the period sends nothing; a tick after the period sends again.
- [x] Marking reviewed before the next period means no email is sent.
- [x] The no-op mailer sends nothing and the app starts without a Resend key.
- [x] Selecting the Resend adapter without a key fails at startup with a clear message.
- [x] The loop starts with the API and stops cleanly on shutdown; a tick failure is logged and does not stop the loop.
- [x] The mailer choice and the interval are settings, documented alongside the model and web-backend settings.
- [x] `make check` and `make test-postgres` pass; `make test-e2e` passes; a dev run with the one-minute interval and the no-op mailer logs a reminder for the test tenant.

## Blocked by

- [04 — Brand DNA review is due](04-brand-dna-review-is-due.md) — completed

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

**2026-09-11 — review (agent).** Standards and spec reviews on `084b1fc`. Resolved in `6acc6fc`: cancelling the loop mid-tick now waits for the tick's thread to finish before the lifespan closes the stores, since a thread cannot be interrupted and a half-done tick would otherwise write to a closed pool, pinned by a test; one business's store error is caught per business, as a failed send already was, so it costs one reminder and not the tick; the email copy moved from `questionnaire/review.py` to `reminders.py` beside the tick that sends it, leaving the review module about the review; the Postgres and in-memory directories write both review timestamps through one helper each; the Resend client follows the Tavily backend's `is not None` idiom; the test handler is typed rather than ignored; the mailer block in `config.py` no longer splits the web-search block; the PRD now names `MARKETING_OS_RESEND_API_KEY` and `dna_reminded_at` as shipped. Decisions kept, on purpose: `MARKETING_OS_MAIL_FROM` is a second required setting for Resend and `MARKETING_OS_APP_URL` a third setting, because Resend only sends from a verified address and the email has to link somewhere — both refused or defaulted with the setting named; the recipient is the signed-in email of whoever last made a request, stored on the tenant row, because the tick has no request and the engine holds no IdP secret (ADR-0013), and a business with no recorded address is skipped with a log line and tried again next tick rather than recorded as reminded; the reminder period rolls from the last reminder, so an untouched review is mentioned once every interval; `ReminderSent` carries the tenant as well as the address, since that is what was sent and to whom; the Resend adapter keeps its own status and timeout constants rather than sharing the Tavily backend's, so removing either adapter stays a delete.

**2026-09-11 — done (agent).** Gates on the reviewed tree (`6acc6fc`; `125fedb` after it is glossary and ADR text only): `make check` 786 passed; `make test-postgres` 916 passed; `make test-e2e` 75 passed in 1.2 min. `make test-e2e` cannot be run as one target from a scratchpad worktree — `pnpm` refuses a `node_modules` that is a symlink into the main checkout — so its three steps were run by hand with the Playwright binary, which is what the target does. The running-app check was made on the e2e stack rather than the dev stack, whose containers belong to the operator and were left alone: the engine log there shows, at startup and again one interval later, `mail.noop to=e2e+clerk_test@example.com subject='Your Brand DNA is due a review'` followed by `reminder.sent tenant=ten_e2e0000000000000000000000000000`, with the no-op mailer and that stack's 20 s interval standing in for the dev stack's minute.

## Completion

- Completed: 2026-09-11
- Commits: `084b1fc` Email the business when its Brand DNA review is due; `6acc6fc` Tighten the reminder email after review; `125fedb` Name the Review Reminder, Contact Email and Mailer in the glossary; on branch `feat/clarifications-05-reminder-email`; status commit and merge recorded below once made.
- Evidence per criterion:
  - One tick sends exactly one email per due tenant and none to tenants not due, fake clock and fake mailer — `tests/test_reminders.py::test_one_tick_reminds_each_due_business_once_and_no_one_else` (one due, one reviewed half a week ago, one with an incomplete DNA), `::test_a_business_becoming_due_later_is_reminded_then`, `::test_the_reminder_names_the_business_and_links_to_the_brand_page`, `::test_a_reminder_is_recorded_on_the_business`; the pure rule in `::test_a_due_review_never_reminded_about_is_due_a_reminder`, `::test_a_review_that_is_not_due_gets_no_reminder_however_long_ago_the_last_was`.
  - A second tick within the period sends nothing; a tick after the period sends again — `::test_a_second_tick_within_the_period_sends_nothing`, `::test_a_tick_after_the_period_reminds_again`, `::test_a_reminder_within_the_period_is_not_sent_again` (boundary: exactly the interval is not again).
  - Marking reviewed before the next period means no email is sent — `::test_a_business_that_reviews_before_the_next_period_is_not_reminded`.
  - The no-op mailer sends nothing and the app starts without a Resend key — `::test_the_no_op_mailer_sends_nothing_and_says_so`, `::test_the_no_op_mailer_is_built_by_default`, `::test_the_app_starts_without_a_resend_key_on_the_no_op_mailer`.
  - Selecting the Resend adapter without a key fails at startup with a clear message — `::test_selecting_resend_without_a_key_stops_the_app_at_startup` (the error names `MARKETING_OS_RESEND_API_KEY`; `get_mailer()` runs in the lifespan before the backend opens), `::test_selecting_resend_without_a_key_is_refused_by_name`, `::test_selecting_resend_without_a_sender_is_refused_by_name`; the Resend adapter itself in `::test_resend_is_asked_to_send_the_message_from_the_configured_sender`, `::test_a_rejected_resend_key_is_a_configuration_error`, `::test_a_failed_send_is_reported_with_what_resend_said`, `::test_a_network_failure_is_reported_as_a_failed_send`.
  - The loop starts with the API and stops cleanly on shutdown; a tick failure is logged and does not stop the loop — `::test_the_reminder_task_starts_with_the_api_and_reminds_a_due_business`, `::test_cancelling_the_loop_lets_the_tick_in_flight_finish_first`, `::test_the_loop_ticks_at_once_then_keeps_going_past_a_failure`; within a tick, `::test_one_failed_send_is_logged_and_the_rest_are_still_sent`, `::test_one_business_whose_answers_cannot_be_read_does_not_cost_the_others_theirs`, `::test_a_due_business_with_no_address_is_skipped_until_one_is_known`.
  - The mailer choice and the interval are settings, documented alongside the model and web-backend settings — `MARKETING_OS_MAILER`, `MARKETING_OS_RESEND_API_KEY`, `MARKETING_OS_MAIL_FROM`, `MARKETING_OS_APP_URL` in `agent-harness/example.env`, `.env.example` and `docs/running-locally.md`, passed through by `docker-compose.yml` and named by `docker-compose.e2e.yml`; parsing in `::test_the_mailer_is_the_no_op_unless_one_is_chosen`, `::test_the_mailer_is_read_from_the_environment`, `::test_a_mailer_that_does_not_exist_is_refused`, `::test_the_resend_key_and_sender_are_read_from_the_environment`, `::test_the_app_url_is_read_without_its_trailing_slash`.
  - `make check`, `make test-postgres`, `make test-e2e` pass; a run with the no-op mailer logs a reminder for the test tenant — the three runs and the engine log lines in the done note above. Storage: `tests/test_postgres.py::test_the_signed_in_email_is_recorded_and_kept_when_a_later_request_has_none`, `::test_every_registered_tenant_is_listed_once`, `::test_a_reminder_is_recorded_and_read_back_by_every_path`; `tests/test_schema_drift.py::test_every_table_declares_the_columns_it_is_checked_for` (the two new columns); seed: `tests/test_seed_test_tenants.py::test_the_seeded_tenant_can_be_emailed_and_the_blank_one_cannot`, `::test_reseeding_forgets_the_last_reminder`, `::test_a_missing_user_email_is_refused`.
