"""Console logging setup for the harness.

Configures stdlib logging under the ``marketing_os`` namespace so a developer
sees a run live on the console. The setup is idempotent — a repeat call does not
stack duplicate handlers.
"""

from __future__ import annotations

import logging

from marketing_os.config import Settings

_LOGGER_NAME = "marketing_os"


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return a logger under the ``marketing_os`` namespace.

    Args:
        name: The logger name; defaults to the package logger.

    Returns:
        The requested logger.
    """
    return logging.getLogger(name)


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure console logging for the harness (idempotent).

    Args:
        settings: The harness settings supplying the log level.

    Returns:
        The configured package logger.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    if not any(getattr(h, "_marketing_os", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
        )
        handler._marketing_os = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger
