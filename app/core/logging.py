"""Shared logging configuration for application entry points."""

from __future__ import annotations

import logging


DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure console logging once without replacing host-provided handlers."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
    else:
        root_logger.setLevel(level)
