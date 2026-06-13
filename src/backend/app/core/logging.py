"""Loguru logger configuration with rotating file sinks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.backend.app.core.config import settings

if TYPE_CHECKING:
    from loguru import Logger

# * Remove default logger configuration
logger.remove()

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)

logger.add(
    sink=LOG_DIR / "debug.log",
    format=LOG_FORMAT,
    level="DEBUG" if settings.ENVIRONMENT == "local" else "INFO",
    filter=lambda record: record["level"].no <= logger.level("WARNING").no,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
)

logger.add(
    sink=LOG_DIR / "error.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)


def get_logger() -> Logger:
    """Return the configured application logger."""
    return logger
