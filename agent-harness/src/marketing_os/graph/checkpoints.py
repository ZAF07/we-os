"""Checkpoint threads — how a run's resumable state is addressed, and abandoned.

LangGraph keys a resumable run by ``thread_id``. Two rules govern what that id
must contain:

**The tenant is part of the id.** Campaign slugs are chosen by businesses, so two
tenants can both run ``spring``. On the in-process checkpointer that collision
was invisible — every run built its own saver — but a durable, shared
checkpointer would hand one business's mid-run state to another. The tenant is
therefore a segment of the thread id, exactly as it is a segment of a document
path (ADR-0013).

**Abandoning is explicit.** With an ephemeral checkpointer, a cancelled run's
state died with the process, so the next run of that campaign necessarily
started at stage 1. Once checkpoints are durable that stops being free:
resuming is the default, and "a cancelled run starts clean" silently becomes
"resume from the last checkpoint" unless the campaign's threads are deleted.
:func:`clear_campaign_threads` deletes them — the full-pipeline thread *and*
every per-stage thread, since a single-stage run checkpoints under its own
(ADR-0014).
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver

from marketing_os.adapters.observability import get_logger
from marketing_os.governance.pipeline import PIPELINE

_LOGGER = get_logger("marketing_os.checkpoints")


def thread_id(tenant: str, slug: str, stage: str | None) -> str:
    """Return the checkpoint thread id for a run.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.
        stage: The single stage being run, or ``None`` for the full pipeline.

    Returns:
        ``<tenant>/<slug>`` for a full run, or ``<tenant>/<slug>:<stage>`` for a
        single-stage run.
    """
    scoped = f"{tenant}/{slug}"
    return f"{scoped}:{stage}" if stage else scoped


def campaign_thread_ids(tenant: str, slug: str) -> list[str]:
    """Return every checkpoint thread a campaign can have written state under.

    Args:
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        The full-pipeline thread id followed by one per pipeline stage.
    """
    return [thread_id(tenant, slug, None)] + [
        thread_id(tenant, slug, stage.key) for stage in PIPELINE
    ]


async def clear_campaign_threads(
    checkpointer: BaseCheckpointSaver | None, tenant: str, slug: str
) -> list[str]:
    """Delete every checkpoint thread for a campaign so its next run starts clean.

    Called when a run is abandoned — cancelled by its owner, or reclaimed after
    the worker executing it died. Without it, a durable checkpointer would
    resume the abandoned run's state on the next start, which is the exact
    behaviour cancelling is supposed to prevent.

    Args:
        checkpointer: The checkpointer holding the threads, or ``None`` when the
            deployment runs without one.
        tenant: The tenant that owns the campaign.
        slug: The campaign slug.

    Returns:
        The thread ids that were cleared, empty when there is no checkpointer.
    """
    if checkpointer is None:
        return []
    cleared = campaign_thread_ids(tenant, slug)
    for thread in cleared:
        await checkpointer.adelete_thread(thread)
    _LOGGER.info("checkpoints.cleared slug=%s threads=%d", slug, len(cleared))
    return cleared
