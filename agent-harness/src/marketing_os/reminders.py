"""The reminder that a Brand DNA review is due, and the task that sends it (ADR-0028).

Facts about a business drift, so when a review is due the owner hears about it
by email, once per review interval. Two pieces, kept apart on purpose:

* :func:`send_due_reminders` is one **tick**: a plain function over the tenant
  directory, the Brand DNA stores, a mailer and a clock. It walks every
  business, judges the review exactly as the API does, sends one email to each
  business that is due and has not been reminded this period, and records the
  reminder. Tests call it directly with a fake clock and a fake mailer.
* :func:`remind_on_interval` is the **loop**: tick now, then every interval,
  inside the single engine process, until cancelled. A failing tick is logged
  and the loop goes on.

There is no job framework and no worker. One loop for one job is what the
single-process service supports (ADR-0025); a dedicated worker waits until a
second job exists.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from marketing_os.adapters.observability import get_logger
from marketing_os.ports import AnswerStore, Mailer, QuestionnaireStore, TenantDirectory
from marketing_os.questionnaire import reminder_due, review_from_stores, review_reminder
from marketing_os.schemas import Tenant

_LOGGER = get_logger("marketing_os.reminders")

BRAND_PAGE_PATH = "/brand"


@dataclass(frozen=True)
class ReminderSent:
    """One reminder a tick sent.

    Attributes:
        tenant_id: The business reminded.
        to: The address it was sent to.
    """

    tenant_id: str
    to: str


def brand_page_url(app_url: str) -> str:
    """Return where the Brand page is, for the reminder to link to.

    Args:
        app_url: Where the web app is reached, without a trailing slash.

    Returns:
        The Brand page URL.
    """
    return f"{app_url}{BRAND_PAGE_PATH}"


def send_due_reminders(
    *,
    tenants: TenantDirectory,
    answers: AnswerStore,
    questionnaires: QuestionnaireStore,
    mailer: Mailer,
    now: datetime,
    interval: timedelta,
    app_url: str,
) -> list[ReminderSent]:
    """Email every business whose review is due and has not been reminded this period.

    One tick. A business is reminded when its review is due and its last
    reminder is absent or older than the interval, so a review left alone is
    mentioned once per period and no more. The reminder is recorded only once
    the message was sent: a business with no known address, or whose send
    failed, is logged and tried again next tick rather than marked as told.

    Args:
        tenants: The directory of every business.
        answers: Each business's Brand DNA answers, which decide completeness.
        questionnaires: The published question set.
        mailer: What sends the email.
        now: The current time.
        interval: The review interval, which is also how long a reminder holds.
        app_url: Where the web app is reached, so the email can link to the
            Brand page.

    Returns:
        The reminders sent, one per business reminded.
    """
    sent: list[ReminderSent] = []
    for tenant in tenants.all():
        review = review_from_stores(
            tenant.tenant_id,
            reviewed_at=tenant.dna_reviewed_at,
            answers=answers,
            questionnaires=questionnaires,
            now=now,
            interval=interval,
        )
        if not reminder_due(review, reminded_at=tenant.dna_reminded_at, now=now, interval=interval):
            continue
        reminder = _remind(tenant, tenants, mailer, now=now, app_url=app_url)
        if reminder is not None:
            sent.append(reminder)
    return sent


def _remind(
    tenant: Tenant,
    tenants: TenantDirectory,
    mailer: Mailer,
    *,
    now: datetime,
    app_url: str,
) -> ReminderSent | None:
    """Send one business its reminder and record it, or say why not.

    Args:
        tenant: The business, due a review and not yet reminded this period.
        tenants: The directory the reminder is recorded in.
        mailer: What sends the email.
        now: The current time, recorded as when the reminder went out.
        app_url: Where the web app is reached.

    Returns:
        The reminder sent, or ``None`` when the business has no address or the
        send failed — both logged, neither recorded, so the next tick tries again.
    """
    if not tenant.contact_email:
        _LOGGER.info("reminder.skipped tenant=%s reason=no address", tenant.tenant_id)
        return None
    message = review_reminder(
        business_name=tenant.name,
        to=tenant.contact_email,
        brand_page_url=brand_page_url(app_url),
    )
    try:
        mailer.send(message)
    except Exception:
        _LOGGER.warning(
            "reminder.failed tenant=%s to=%s", tenant.tenant_id, tenant.contact_email, exc_info=True
        )
        return None
    tenants.mark_dna_reminded(tenant.tenant_id, at=now)
    _LOGGER.info("reminder.sent tenant=%s to=%s", tenant.tenant_id, tenant.contact_email)
    return ReminderSent(tenant_id=tenant.tenant_id, to=tenant.contact_email)


async def remind_on_interval(tick: Callable[[], object], every: timedelta) -> None:
    """Run a tick now and then every interval, until cancelled.

    The tick runs in a worker thread because the stores behind it are
    synchronous, so a slow database or mail provider never stalls the API
    serving requests on the event loop. A tick that raises is logged and the
    loop waits for the next one: a reminder is worth less than the service
    staying up, and the next tick will send whatever this one did not.

    Args:
        tick: The function to run each time.
        every: How long to wait between ticks.
    """
    while True:
        try:
            await asyncio.to_thread(tick)
        except Exception:
            _LOGGER.exception("reminders.tick_failed")
        await asyncio.sleep(every.total_seconds())
