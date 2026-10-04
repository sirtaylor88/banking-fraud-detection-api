"""NextGen Bank FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
import svcs

from src.backend.app.api.main import api_router
from src.backend.app.core.config import settings
from src.backend.app.core.db import db_session_factory, engine


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown via svcs service registry.

    Registers the async database session factory with svcs and disposes
    the SQLAlchemy engine on shutdown.

    Args:
        fastapi_app: The FastAPI application instance.
    """
    registry = svcs.Registry()
    registry.register_factory(AsyncSession, db_session_factory)
    fastapi_app.state.svcs_registry = registry

    yield

    await engine.dispose()
    await registry.aclose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)
