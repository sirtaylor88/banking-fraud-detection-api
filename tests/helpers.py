"""Shared test helpers."""

from unittest.mock import AsyncMock, MagicMock


def async_cm(value: object = None) -> MagicMock:
    """Build an async context manager mock.

    Args:
        value: The object returned by ``__aenter__``.

    Returns:
        MagicMock: The async context manager.
    """
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm
