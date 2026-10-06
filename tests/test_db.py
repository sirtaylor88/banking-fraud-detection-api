"""Tests for database session factory and initialization."""

from collections.abc import AsyncGenerator, Iterator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.app.core.db import db_session_factory, init_db
from tests.helpers import async_cm

DB = "src.backend.app.core.db"


@pytest.fixture(name="mock_session")
def fixture_mock_session() -> Iterator[AsyncMock]:
    """Patch the session factory to hand out a mock session.

    Yields:
        AsyncMock: The mock session.
    """
    session = AsyncMock(spec=AsyncSession)
    with patch(f"{DB}.async_session", return_value=async_cm(session)):
        yield session


@pytest.mark.anyio
async def test_db_session_factory_yields_session(mock_session: AsyncMock) -> None:
    """Test that db_session_factory yields a session and closes it."""
    gen: AsyncGenerator[AsyncSession, None] = db_session_factory()
    assert await gen.__anext__() is mock_session
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

    mock_session.rollback.assert_not_called()
    mock_session.close.assert_called_once()


@pytest.mark.anyio
@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_db_session_factory_rollback_on_exception(
    mock_session: AsyncMock, cleanup_fails: bool
) -> None:
    """Test that errors roll back and re-raise, even if rollback/close fail."""
    if cleanup_fails:
        mock_session.rollback.side_effect = RuntimeError("rollback failed")
        mock_session.close.side_effect = RuntimeError("close failed")

    gen: AsyncGenerator[AsyncSession, None] = db_session_factory()
    await gen.__anext__()
    exc = ValueError("db error")
    with pytest.raises(ValueError, match="db error"):
        await gen.athrow(exc)

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


@pytest.mark.anyio
async def test_init_db_success() -> None:
    """Test that init_db verifies the connection on the first attempt."""
    conn = AsyncMock()
    with patch(f"{DB}.engine") as engine:
        engine.begin.return_value = async_cm(conn)
        await init_db()

    conn.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_init_db_retries_then_raises() -> None:
    """Test that init_db retries with back-off and re-raises after the last try."""
    with (
        patch(f"{DB}.engine") as engine,
        patch(f"{DB}.asyncio.sleep", new_callable=AsyncMock) as sleep,
    ):
        engine.begin.side_effect = ConnectionError("db down")
        with pytest.raises(ConnectionError):
            await init_db()

    assert engine.begin.call_count == 3
    assert [c.args[0] for c in sleep.await_args_list] == [2, 4]
