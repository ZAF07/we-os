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
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta

from marketing_os.adapters.observability import get_logger
from marketing_os.ports import AnswerStore, Mailer, QuestionnaireStore, TenantDirectory
from marketing_os.questionnaire import reminder_due, review_from_stores
from marketing_os.schemas import EmailMessage, Tenant

_LOGGER = get_logger("marketing_os.reminders")

_BRAND_PAGE_PATH = "/brand"

REVIEW_REMINDER_SUBJECT = "Your Brand DNA is due a review"


@dataclass(frozen=True)
class ReminderSent:
    """One reminder a tick sent.

    Attributes:
        tenant_id: The business reminded.
        to: The address it was sent to.
    """

    tenant_id: str
    to: str


def review_reminder(*, business_name: str, to: str, brand_page_url: str) -> EmailMessage:
    """Write the email telling a business its Brand DNA is due a review.

    It says what is true and asks for one thing: that the owner look, and mark
    the review done. It promises nothing the product does not do.

    Args:
        business_name: The business, as it named itself.
        to: The address to send it to.
        brand_page_url: Where the Brand page is, so the owner can go straight there.

    Returns:
        The message.
    """
    text = (
        f"Hi,\n\n"
        f"It has been a while since {business_name} looked at its Brand DNA. "
        f"Businesses change, and every campaign We-OS plans rests on what your Brand DNA "
        f"says — so it is worth a few minutes to check it still holds.\n\n"
        f"Have a look at your Brand page and mark it reviewed when you are done:\n"
        f"{brand_page_url}\n\n"
        f"If anything has changed, edit the answer there and We-OS will use the new one "
        f"from your next campaign onward.\n\n"
        f"We-OS"
    )
    return EmailMessage(to=to, subject=REVIEW_REMINDER_SUBJECT, text=text)


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
        try:
            reminder = _remind_if_due(
                tenant,
                tenants=tenants,
                answers=answers,
                questionnaires=questionnaires,
                mailer=mailer,
                now=now,
                interval=interval,
                app_url=app_url,
            )
        except Exception:
            _LOGGER.warning("reminder.failed tenant=%s", tenant.tenant_id, exc_info=True)
            continue
        if reminder is not None:
            sent.append(reminder)
    return sent


def _remind_if_due(
    tenant: Tenant,
    *,
    tenants: TenantDirectory,
    answers: AnswerStore,
    questionnaires: QuestionnaireStore,
    mailer: Mailer,
    now: datetime,
    interval: timedelta,
    app_url: str,
) -> ReminderSent | None:
    """Judge one business's review and, when a reminder is owed, send and record it.

    Args:
        tenant: The business.
        tenants: The directory the reminder is recorded in.
        answers: Its Brand DNA answers.
        questionnaires: The published question set.
        mailer: What sends the email.
        now: The current time.
        interval: The review interval.
        app_url: Where the web app is reached.

    Returns:
        The reminder sent, or ``None`` when none was owed or the business has
        no address — the latter logged and not recorded, so the next tick tries
        again once one is known.

    Raises:
        Exception: Whatever a store or the mailer raised; the caller logs it
            and moves on to the next business, so one failure costs one
            reminder rather than the tick.
    """
    review = review_from_stores(
        tenant.tenant_id,
        reviewed_at=tenant.dna_reviewed_at,
        answers=answers,
        questionnaires=questionnaires,
        now=now,
        interval=interval,
    )
    if not reminder_due(review, reminded_at=tenant.dna_reminded_at, now=now, interval=interval):
        return None
    if not tenant.contact_email:
        _LOGGER.info("reminder.skipped tenant=%s reason=no address", tenant.tenant_id)
        return None
    mailer.send(
        review_reminder(
            business_name=tenant.name,
            to=tenant.contact_email,
            brand_page_url=f"{app_url}{_BRAND_PAGE_PATH}",
        )
    )
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

    Cancelling the loop mid-tick lets that tick finish first. A thread cannot
    be interrupted, and the caller closes the stores as soon as this returns,
    so returning early would leave the tick writing to a closed pool.

    Args:
        tick: The function to run each time.
        every: How long to wait between ticks.
    """
    while True:
        try:
            await _run_to_completion(tick)
        except Exception:
            _LOGGER.exception("reminders.tick_failed")
        await asyncio.sleep(every.total_seconds())


async def _run_to_completion(tick: Callable[[], object]) -> None:
    """Run one tick in a worker thread, finishing it even if cancelled meanwhile.

    Args:
        tick: The function to run.

    Raises:
        asyncio.CancelledError: After the in-flight tick has finished, when the
            caller was cancelled while it ran.
        Exception: Whatever the tick raised.
    """
    in_flight = asyncio.ensure_future(asyncio.to_thread(tick))
    try:
        await asyncio.shield(in_flight)
    except asyncio.CancelledError:
        with suppress(Exception):
            await in_flight
        raise
