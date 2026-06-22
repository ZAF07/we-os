"""Run checkpointing — persist a campaign run's state so it can resume.

A run accumulates its deliverables in ADK session state (keys like ``intake``,
``research``, ``strategy``, …). That state is in-memory, so a crash or a transient
model error (e.g. a Gemini 503) loses everything. This module persists the
relevant state to a small JSON file next to the campaign
(`campaigns/<slug>/.run_state.json`) after each stage, and reloads it to
**pre-seed** a new run — so completed stages are skipped and the run continues
where it left off. Used identically by the CLI and the API.

The checkpoint is plain JSON on purpose: transparent, inspectable, and free of
extra dependencies (no database/session service required).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .config import Settings

#: Ordered pipeline deliverable keys (mirrors pipeline.DELIVERABLE_KEYS). A stage
#: counts as complete once its key is present in the checkpoint.
STAGE_ORDER = [
    "intake",
    "research",
    "strategy",
    "campaign_strategy",
    "creative",
    "asset_prompts",
    "media",
    "eval",
    "execution",
    "performance",
]

# State keys NOT worth persisting / not JSON-safe go here; everything else that
# json-serializes is kept (deliverables, *_raw, steps, violations, notes, seed).
_SKIP_PREFIXES = ("temp:", "_")


def checkpoint_path(settings: Settings, slug: str) -> Path:
    """Return the checkpoint file path for a campaign slug."""
    return settings.campaigns_dir / slug / ".run_state.json"


def load_checkpoint(settings: Settings, slug: str) -> Optional[dict]:
    """Load a prior run's persisted state, or None if there is no checkpoint."""
    path = checkpoint_path(settings, slug)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_checkpoint(settings: Settings, slug: str, state: dict) -> None:
    """Persist the JSON-serializable subset of `state` atomically.

    Args:
        settings: Resolved settings (locates the campaign dir).
        slug: Campaign slug.
        state: The accumulated run state (seed + deliverables + traces).
    """
    path = checkpoint_path(settings, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe: dict[str, Any] = {}
    for key, value in state.items():
        if key.startswith(_SKIP_PREFIXES):
            continue
        try:
            json.dumps(value)  # keep only what round-trips through JSON
        except (TypeError, ValueError):
            continue
        safe[key] = value
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(safe, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic on POSIX


def clear_checkpoint(settings: Settings, slug: str) -> None:
    """Delete a campaign's checkpoint (used for a `--fresh` run)."""
    checkpoint_path(settings, slug).unlink(missing_ok=True)


def completed_stages(state: dict) -> list[str]:
    """Return the pipeline stages already present in `state`, in order."""
    return [k for k in STAGE_ORDER if state.get(k) not in (None, "", [], {})]


def eval_passed(state: dict) -> bool:
    """True if the Evaluator's verdict in state indicates a pass.

    The Evaluator's deliverable is stored as JSON (string or dict); parse
    defensively and read ``passed``.
    """
    verdict = state.get("eval")
    if isinstance(verdict, str):
        verdict = _loads_lenient(verdict)
    return bool(verdict.get("passed")) if isinstance(verdict, dict) else False


def _loads_lenient(text: str) -> dict:
    """Parse JSON that may be wrapped in markdown fences or surrounded by prose.

    The prompt-based structured-output path (providers without JSON-schema
    response_format) can return fenced JSON; tolerate it.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}
