"""Load a local ``.env`` at process startup.

Kept out of ``config.py`` on purpose: loading a ``.env`` is an entrypoint
concern with an import-time side effect (it mutates ``os.environ``), while the
config/adapter layer stays free of such side effects so it resolves purely from
whatever environment it is handed. Each process entrypoint calls :func:`load_env`
once, early, before settings are read.
"""

from __future__ import annotations

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    """Load a local ``.env`` into the process environment, if one exists.

    Resolves ``.env`` by walking up from the current working directory, so a
    developer running from the repo picks it up without a manual ``source``.
    Values already present in the environment win (``override=False``), so real
    environment and CI values are never clobbered by a local ``.env``; a missing
    ``.env`` is a silent no-op.
    """
    load_dotenv(find_dotenv(usecwd=True), override=False)
