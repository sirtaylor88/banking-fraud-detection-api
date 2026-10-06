"""NextGen Bank FastAPI application."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import svcs

from src.backend.app.api.main import api_router
from src.backend.app.core.config import settings
from src.backend.app.core.constants import STARTUP_TIMEOUT
from src.backend.app.core.db import db_session_factory, engine, init_db
from src.backend.app.core.health import ServiceStatus, health_checker
from src.backend.app.core.logging import get_logger

logger = get_logger()


async def shutdown(registry: svcs.Registry) -> None:
    """Release application resources.

    Args:
        registry: The svcs registry to close.
    """
    await health_checker.cleanup()
    await registry.aclose()
    await engine.dispose()


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    On startup, registers the async database session factory with svcs,
    verifies the database connection, registers the database, Redis and
    Celery health checks, and waits up to ``STARTUP_TIMEOUT`` seconds for
    all services to be healthy. On
    shutdown (or failed startup), clears the health checker, closes the
    svcs registry and disposes the SQLAlchemy engine.

    Args:
        fastapi_app: The FastAPI application instance.

    Yields:
        None: Control to the running application.

    Raises:
        RuntimeError: If critical services are not healthy at startup.
    """
    registry = svcs.Registry()
    registry.register_factory(AsyncSession, db_session_factory)
    fastapi_app.state.svcs_registry = registry

    try:
        await init_db()
        logger.info("Database initialized successfully!")

        await health_checker.add_service("database", health_checker.check_database)
        await health_checker.add_service("redis", health_checker.check_redis)
        await health_checker.add_service("celery", health_checker.check_celery)

        try:
            async with asyncio.timeout(STARTUP_TIMEOUT):
                await health_checker.wait_for_services()
        except TimeoutError as err:
            raise RuntimeError("Critical services failed to start!") from err

        logger.info("All services initialized and healthy.")

    except Exception as err:
        logger.error(f"Application startup failed: {err}")
        await shutdown(registry)
        raise

    try:
        yield
    finally:
        logger.info("Shutting down ...")
        await shutdown(registry)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


@app.get("/health", response_model=dict)
async def health_check() -> JSONResponse:
    """Report the aggregated health of all registered services.

    Returns:
        JSONResponse: The health report with status 200 when healthy, 206 when
        degraded, 503 when unhealthy and 500 if the check itself fails.
    """
    try:
        health_status = await health_checker.check_all_services()
        if health_status["status"] == ServiceStatus.HEALTHY:
            status_code = status.HTTP_200_OK
        elif health_status["status"] == ServiceStatus.DEGRADED:
            status_code = status.HTTP_206_PARTIAL_CONTENT
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(content=health_status, status_code=status_code)

    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.error(f"Health check failed: {err}")
        return JSONResponse(
            content={"status": ServiceStatus.UNHEALTHY, "error": str(err)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


app.include_router(api_router, prefix=settings.API_V1_STR)
