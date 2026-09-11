# 04 — Brand DNA review is due

Status: ready-for-agent
Type: task

## Parent

[PRD: Clarifications](../PRD.md) · [ADR-0028](../../../docs/adr/0028-clarifications-are-brand-dna-the-specialist-asks-for.md)

## What to build

The platform tells the business owner, in the app, when it is time to look at their Brand DNA again.

The tenant record gains a reviewed-at timestamp. A review is **due** when now minus reviewed-at exceeds a new interval setting, one minute in dev and a week in production. A tenant that has never reviewed counts from when its DNA was first completed. Reviewed-at is set by a new mark-reviewed endpoint and by saving any questionnaire or Clarification answer, so the owner is never asked to review what they just edited.

On Home, the Action Queue shows an amber **Review** item when a review is due, linking to the Brand page. The Brand page shows a Reviewed action while a review is due; clicking it clears the item. The empty-state copy names a due review as one reason an item appears.

Due-ness is derived from the timestamp on every read, never stored, so the item cannot drift from the truth. This issue does not send email; the next one does, from the same timestamp.

## Acceptance criteria

- [ ] The Home payload carries a Review item exactly when now minus reviewed-at exceeds the configured interval, with a fake clock in the API tests.
- [ ] Mark-reviewed, saving a questionnaire answer, and saving a Clarification answer each clear the item.
- [ ] A tenant whose DNA was just completed is not due until the interval has passed.
- [ ] The interval is read from settings; changing it changes due-ness on the next read with no restart of the test app.
- [ ] Home shows the amber Review item in the browser suite; the Brand page's Reviewed action clears it.
- [ ] `make check` and `make test-postgres` pass; `make test-e2e` passes; the item and the Reviewed action are confirmed in the running app.

## Blocked by

None - can start immediately.
