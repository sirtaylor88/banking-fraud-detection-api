"""Database engine and session factory."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.backend.app.core.config import settings
from src.backend.app.core.constants import (
    DB_INIT_MAX_RETRIES,
    DB_INIT_RETRY_DELAY,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)
from src.backend.app.core.logging import get_logger

logger = get_logger()


def db_connect_args(schema: str) -> dict[str, Any]:
    """Build asyncpg connection arguments that select a schema.

    asyncpg rejects unknown connection parameters such as ``schema``, so the
    schema is applied as the ``search_path`` server setting instead.

    Args:
        schema: Schema name; an empty string keeps the server's default.

    Returns:
        dict[str, Any]: Keyword arguments for ``asyncpg.connect()``.
    """
    if not schema:
        return {}
    return {"server_settings": {"search_path": schema}}


engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    connect_args=db_connect_args(settings.POSTGRES_SCHEMA),
)
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def db_session_factory() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use with svcs.

    Rolls back and re-raises on any exception; always closes the session on exit.

    Yields:
        AsyncSession: An active database session.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as err:
            logger.error(f"Database session error: {err}")

            if session:
                try:
                    await session.rollback()
                    logger.info(
                        "Successfully rolled back the database session after error."
                    )
                except Exception as rollback_error:  # pylint: disable=broad-exception-caught
                    logger.error(
                        f"Error during database session rollback: {rollback_error}"
                    )

            raise

        finally:
            if session:
                try:
                    await session.close()
                    logger.debug("Database session closed successfully!")
                except Exception as close_err:  # pylint: disable=broad-exception-caught
                    logger.error(f"Error closing database session: {close_err}")


async def init_db() -> None:
    """Init the database."""
    try:
        for attempt in range(DB_INIT_MAX_RETRIES):
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))

                logger.info("Database connection verified successfully!")
                break

            except Exception:  # pylint: disable=broad-exception-caught
                if attempt == DB_INIT_MAX_RETRIES - 1:
                    logger.error(
                        "Failed to verify database connection after "
                        f"{DB_INIT_MAX_RETRIES} attempts."
                    )
                    raise

                logger.warning(f"Database connection attempt {attempt + 1}.")
                await asyncio.sleep(DB_INIT_RETRY_DELAY * (attempt + 1))

    except Exception as err:
        logger.error(f"Database initialization failed: {err}")
        raise
