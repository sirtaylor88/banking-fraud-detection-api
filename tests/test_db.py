"""Tests for database session factory."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.app.core.db import db_session_factory


@pytest.mark.anyio
async def test_db_session_factory_yields_session() -> None:
    """Test that db_session_factory yields a session successfully."""
    mock_session: AsyncMock = AsyncMock(spec=AsyncSession)
    mock_cm: AsyncMock = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("src.backend.app.core.db.async_session", return_value=mock_cm):
        gen: AsyncGenerator[AsyncSession, None] = db_session_factory()
        session: AsyncSession = await gen.__anext__()
        assert session is mock_session
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    mock_session.close.assert_called_once()


@pytest.mark.anyio
async def test_db_session_factory_rollback_on_exception() -> None:
    """Test that db_session_factory rolls back and re-raises on exception."""
    mock_session: AsyncMock = AsyncMock(spec=AsyncSession)
    mock_cm: AsyncMock = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("src.backend.app.core.db.async_session", return_value=mock_cm):
        gen: AsyncGenerator[AsyncSession, None] = db_session_factory()
        await gen.__anext__()
        exc = ValueError("db error")
        with pytest.raises(ValueError):
            await gen.athrow(exc)

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()
