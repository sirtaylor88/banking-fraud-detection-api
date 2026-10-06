"""Loguru logger configuration with rotating file sinks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.backend.app.core.config import settings
from src.backend.app.core.constants import (
    LOG_DIR,
    LOG_FORMAT,
    LOG_RETENTION,
    LOG_ROTATION,
)

if TYPE_CHECKING:
    from loguru import Logger

# * Remove default logger configuration
logger.remove()

logger.add(
    sink=LOG_DIR / "debug.log",
    format=LOG_FORMAT,
    level="DEBUG" if settings.ENVIRONMENT == "local" else "INFO",
    filter=lambda record: record["level"].no <= logger.level("WARNING").no,
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION,
    compression="zip",
)

logger.add(
    sink=LOG_DIR / "error.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION,
    compression="zip",
    backtrace=True,
    diagnose=True,
)


def get_logger() -> Logger:
    """Return the configured application logger."""
    return logger
