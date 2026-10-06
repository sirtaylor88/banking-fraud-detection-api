"""Health check module for monitoring service status."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import time
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import text

from src.backend.app.core.celery_app import celery_app
from src.backend.app.core.config import settings
from src.backend.app.core.constants import (
    CELERY_BROKER_MAX_RETRIES,
    HEALTH_CACHE_DURATION,
    HEALTH_CHECK_MAX_RETRIES,
    HEALTH_CHECK_RETRY_DELAY,
    HEALTH_CHECK_TIMEOUT,
    HEALTH_WAIT_RETRY_INTERVALS,
)
from src.backend.app.core.db import async_session
from src.backend.app.core.logging import get_logger

logger = get_logger()


def _now() -> datetime:
    """Return the current UTC time.

    Returns:
        datetime: The current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


class ServiceStatus(StrEnum):
    """Service status values for health checks."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    DOWN = "down"


@dataclass
class ServiceConfig:
    """Health check settings of a registered service."""

    check_function: Callable[[], Awaitable[bool]]
    timeout: float
    retry_delay: float
    max_retries: int
    dependencies: set[str] = field(default_factory=set)


class HealthCheck:
    """Health check class to manage service status."""

    def __init__(self) -> None:
        """Initialize the HealthCheck instance."""
        self._services: dict[str, ServiceStatus] = {}
        self._configs: dict[str, ServiceConfig] = {}
        self._last_check: dict[str, datetime] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

        self._cache_duration: timedelta = HEALTH_CACHE_DURATION
        self._cached_status: dict[str, Any] | None = None
        self._last_check_time: datetime | None = None

    def validate_dependencies(
        self,
        service_name: str,
        depends_on: list[str],
    ) -> None:
        """Ensure every dependency of a service is already registered.

        Args:
            service_name: Name of the service being registered.
            depends_on: Names of the services it depends on.

        Raises:
            ValueError: If a dependency has not been registered.
        """
        for dep in depends_on:
            if dep not in self._services:
                raise ValueError(
                    f"Dependency `{dep}` not registered for service `{service_name}`"
                )

    async def add_service(  # pylint: disable=too-many-arguments
        self,
        service_name: str,
        check_function: Callable[[], Awaitable[bool]],
        *,
        timeout: float = HEALTH_CHECK_TIMEOUT,
        retry_delay: float = HEALTH_CHECK_RETRY_DELAY,
        max_retries: int = HEALTH_CHECK_MAX_RETRIES,
        depends_on: list[str] | None = None,
    ) -> None:
        """Register a service and its health check function.

        Args:
            service_name: Unique name of the service.
            check_function: Coroutine function returning True when healthy.
            timeout: Seconds allowed for a single check attempt.
            retry_delay: Seconds to wait between failed attempts.
            max_retries: Number of attempts before marking the service unhealthy.
            depends_on: Names of already registered services this one depends on.

        Raises:
            ValueError: If a dependency has not been registered.
        """
        if depends_on:
            self.validate_dependencies(service_name, depends_on)

        async with self._lock:
            self._services[service_name] = ServiceStatus.STARTING
            self._configs[service_name] = ServiceConfig(
                check_function=check_function,
                timeout=timeout,
                retry_delay=retry_delay,
                max_retries=max_retries,
                dependencies=set(depends_on or []),
            )
            self._last_check[service_name] = _now()

        if depends_on:
            logger.info(
                f"Service `{service_name}` registered with dependencies: {depends_on}"
            )

    async def check_database(self) -> bool:
        """Check database health.

        Returns:
            bool: True if the database answers a trivial query, False otherwise.
        """
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))

            self._last_check["database"] = _now()
            logger.debug("Database health check passed.")
            return True

        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.error(f"Database health check failed: {err}")
            return False

    async def check_redis(self) -> bool:
        """Check Redis health.

        Returns:
            bool: True if Redis answers a ping, False otherwise.
        """
        try:
            async with Redis.from_url(settings.REDIS_URL) as client:
                await client.ping()

            self._last_check["redis"] = _now()
            return True

        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.error(f"Redis health check failed: {err}")
            return False

    async def check_celery(self) -> bool:
        """Check Celery health.

        Healthy when at least one worker answers a ping, or when no worker
        answers but the RabbitMQ broker is reachable.

        Returns:
            bool: True if workers or the broker are reachable, False otherwise.
        """
        try:
            workers = await asyncio.to_thread(celery_app.control.inspect().ping)

            if not workers:
                await asyncio.to_thread(self._ensure_broker_connection)
                logger.warning("No Celery workers found, but RabbitMQ is reachable.")

            self._last_check["celery"] = _now()
            return True

        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.error(f"Celery health check failed: {err}")
            return False

    @staticmethod
    def _ensure_broker_connection() -> None:
        """Open and close a connection to the Celery broker.

        Raises:
            Exception: If the broker cannot be reached after retries.
        """
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=CELERY_BROKER_MAX_RETRIES)

    async def _dependencies_healthy(self, service_name: str) -> bool:
        """Check that every dependency of a service is healthy.

        Args:
            service_name: Name of a registered service.

        Returns:
            bool: True if all dependencies are healthy, False otherwise.
        """
        for dep in self._configs[service_name].dependencies:
            if await self.check_service_health(dep) != ServiceStatus.HEALTHY:
                logger.error(f"Dependency {dep} not healthy for service {service_name}")
                return False
        return True

    async def _set_status(self, service_name: str, status: ServiceStatus) -> None:
        """Record the status of a service.

        Args:
            service_name: Name of a registered service.
            status: The new status.
        """
        async with self._lock:
            self._services[service_name] = status
            if status == ServiceStatus.HEALTHY:
                self._last_check[service_name] = _now()

    @staticmethod
    async def _run_check(config: ServiceConfig) -> str | None:
        """Run a single health check attempt within its timeout.

        Args:
            config: Settings of the service to check.

        Returns:
            str | None: None if the service is healthy, otherwise the reason.
        """
        try:
            async with asyncio.timeout(config.timeout):
                if await config.check_function():
                    return None
            return "Check returned unhealthy."
        except TimeoutError:
            return f"Timeout after {config.timeout}s."
        except Exception as err:  # pylint: disable=broad-exception-caught
            return str(err)

    async def check_service_health(
        self,
        service_name: str,
    ) -> ServiceStatus:
        """Check health of a service, retrying on failure.

        A service whose dependencies are not all healthy is reported as degraded
        without running its own check.

        Args:
            service_name: Name of a registered service.

        Returns:
            ServiceStatus: The resulting status of the service.

        Raises:
            ValueError: If the service is not registered.
        """
        if service_name not in self._configs:
            raise ValueError(f"Unknown service: {service_name}")

        if not await self._dependencies_healthy(service_name):
            await self._set_status(service_name, ServiceStatus.DEGRADED)
            return ServiceStatus.DEGRADED

        config = self._configs[service_name]
        last_error: str | None = None

        for attempt in range(1, config.max_retries + 1):
            last_error = await self._run_check(config)

            if last_error is None:
                await self._set_status(service_name, ServiceStatus.HEALTHY)
                if attempt > 1:
                    logger.info(
                        f"Service {service_name} recovered after {attempt} attempts."
                    )
                return ServiceStatus.HEALTHY

            await self._set_status(service_name, ServiceStatus.DEGRADED)
            if attempt < config.max_retries:
                await asyncio.sleep(config.retry_delay)

        await self._set_status(service_name, ServiceStatus.UNHEALTHY)
        logger.error(
            f"Service {service_name} unhealthy after {config.max_retries} attempts: "
            f"{last_error}"
        )
        return ServiceStatus.UNHEALTHY

    async def check_all_services(self, use_cache: bool = True) -> dict[str, Any]:
        """Check all registered services concurrently.

        Args:
            use_cache: Return the previous result if it is younger than the
                cache duration.

        Returns:
            dict[str, Any]: Overall status, timestamp and per-service details.
        """
        current_time = _now()
        if (
            use_cache
            and self._cached_status is not None
            and self._last_check_time is not None
            and (current_time - self._last_check_time) < self._cache_duration
        ):
            return self._cached_status

        async with self._lock:
            services = list(self._services)

        results = await asyncio.gather(
            *(self.check_service_health(service) for service in services),
            return_exceptions=True,
        )

        overall = ServiceStatus.HEALTHY
        services_status: dict[str, dict[str, str]] = {}

        for service, result in zip(services, results):
            last_check = self._last_check[service].isoformat()
            if isinstance(result, BaseException):
                services_status[service] = {
                    "status": ServiceStatus.UNHEALTHY,
                    "error": str(result),
                    "last_check": last_check,
                }
                overall = ServiceStatus.DEGRADED
            else:
                services_status[service] = {
                    "status": result,
                    "last_check": last_check,
                }
                if result != ServiceStatus.HEALTHY:
                    overall = ServiceStatus.DEGRADED

        health_status: dict[str, Any] = {
            "status": overall,
            "timestamp": current_time.isoformat(),
            "services": services_status,
        }

        self._cached_status = health_status
        self._last_check_time = current_time

        return health_status

    async def wait_for_services(self) -> None:
        """Poll all services, bypassing the cache, until they are all healthy.

        The delay between polls grows with the elapsed time. The wait is
        unbounded: wrap the call in ``asyncio.timeout()`` to limit it.
        """
        start_time = time.monotonic()

        while (await self.check_all_services(use_cache=False))[
            "status"
        ] != ServiceStatus.HEALTHY:
            elapsed = time.monotonic() - start_time
            wait_time = HEALTH_WAIT_RETRY_INTERVALS[
                min(len(HEALTH_WAIT_RETRY_INTERVALS) - 1, int(elapsed // 10))
            ]
            logger.warning(f"Services not healthy, waiting {wait_time}s before retry.")
            await asyncio.sleep(wait_time)

    async def cleanup(self) -> None:
        """Unregister all services and clear the cached status."""
        async with self._lock:
            self._services.clear()
            self._configs.clear()
            self._last_check.clear()
            self._cached_status = None
            self._last_check_time = None


health_checker = HealthCheck()
