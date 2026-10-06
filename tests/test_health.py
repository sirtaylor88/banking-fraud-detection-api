"""Tests for the health check module."""

import asyncio
from collections.abc import Iterator
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.backend.app.core.constants import CELERY_BROKER_MAX_RETRIES
from src.backend.app.core.health import HealthCheck, ServiceStatus
from tests.helpers import async_cm

HEALTH = "src.backend.app.core.health"


@pytest.fixture(name="checker")
def fixture_checker() -> HealthCheck:
    """Provide a fresh HealthCheck instance.

    Returns:
        HealthCheck: An empty health checker.
    """
    return HealthCheck()


@pytest.fixture(name="no_sleep")
def fixture_no_sleep() -> Iterator[AsyncMock]:
    """Make ``asyncio.sleep`` in the health module return immediately.

    Yields:
        AsyncMock: The patched sleep.
    """
    with patch(f"{HEALTH}.asyncio.sleep", new_callable=AsyncMock) as sleep:
        yield sleep


# * Registration


@pytest.mark.anyio
async def test_add_service_with_dependencies(checker: HealthCheck) -> None:
    """Test registering a service that depends on another one."""
    await checker.add_service("database", AsyncMock(return_value=True))
    await checker.add_service(
        "api", AsyncMock(return_value=True), depends_on=["database"]
    )

    status = await checker.check_service_health("api")

    assert status == ServiceStatus.HEALTHY


@pytest.mark.anyio
async def test_add_service_unknown_dependency(checker: HealthCheck) -> None:
    """Test that an unregistered dependency is rejected."""
    check = AsyncMock(return_value=True)
    with pytest.raises(ValueError, match="Dependency `database` not registered"):
        await checker.add_service("api", check, depends_on=["database"])


# * Individual checks


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected"), [(None, True), (RuntimeError("db down"), False)]
)
async def test_check_database(
    checker: HealthCheck, error: Exception | None, expected: bool
) -> None:
    """Test the database check passes only when the query runs."""
    session = AsyncMock()
    session.execute.side_effect = error
    with patch(f"{HEALTH}.async_session", return_value=async_cm(session)):
        assert await checker.check_database() is expected

    session.execute.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected"), [(None, True), (ConnectionError("redis down"), False)]
)
async def test_check_redis(
    checker: HealthCheck, error: Exception | None, expected: bool
) -> None:
    """Test the Redis check passes only when Redis answers a ping."""
    client = AsyncMock()
    client.ping.side_effect = error
    with patch(f"{HEALTH}.Redis.from_url", return_value=async_cm(client)):
        assert await checker.check_redis() is expected

    client.ping.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("workers", "broker_error", "expected"),
    [
        pytest.param({"w1": {"ok": "pong"}}, None, True, id="workers"),
        pytest.param(None, None, True, id="broker-only"),
        pytest.param(None, ConnectionError("broker down"), False, id="broker-down"),
    ],
)
async def test_check_celery(
    checker: HealthCheck,
    workers: dict[str, dict[str, str]] | None,
    broker_error: Exception | None,
    expected: bool,
) -> None:
    """Test the Celery check falls back to the broker when no worker answers."""
    with patch(f"{HEALTH}.celery_app") as app:
        app.control.inspect.return_value.ping.return_value = workers
        conn = app.connection.return_value.__enter__.return_value
        conn.ensure_connection.side_effect = broker_error
        assert await checker.check_celery() is expected

    if workers:
        app.connection.assert_not_called()
    else:
        conn.ensure_connection.assert_called_once_with(
            max_retries=CELERY_BROKER_MAX_RETRIES
        )


# * Service health with retries


@pytest.mark.anyio
async def test_check_service_health_unknown(checker: HealthCheck) -> None:
    """Test that checking an unregistered service raises."""
    with pytest.raises(ValueError, match="Unknown service: missing"):
        await checker.check_service_health("missing")


@pytest.mark.anyio
async def test_check_service_health_recovers(
    checker: HealthCheck, no_sleep: AsyncMock
) -> None:
    """Test that a service failing then passing is reported healthy."""
    check = AsyncMock(side_effect=[False, RuntimeError("flaky"), True])
    await checker.add_service("svc", check, retry_delay=0.5)

    assert await checker.check_service_health("svc") == ServiceStatus.HEALTHY
    assert check.await_count == 3
    assert no_sleep.await_count == 2


@pytest.mark.anyio
async def test_check_service_health_unhealthy_after_retries(
    checker: HealthCheck, no_sleep: AsyncMock
) -> None:
    """Test that a service failing every attempt is reported unhealthy."""
    check = AsyncMock(return_value=False)
    await checker.add_service("svc", check, max_retries=2)

    assert await checker.check_service_health("svc") == ServiceStatus.UNHEALTHY
    assert check.await_count == 2
    no_sleep.assert_awaited_once()


@pytest.mark.anyio
async def test_check_service_health_timeout(checker: HealthCheck) -> None:
    """Test that a check exceeding its timeout counts as a failure."""

    async def slow() -> bool:
        await asyncio.sleep(1)
        return True  # pragma: no cover

    await checker.add_service("svc", slow, timeout=0.01, max_retries=1)

    assert await checker.check_service_health("svc") == ServiceStatus.UNHEALTHY


@pytest.mark.anyio
@pytest.mark.usefixtures("no_sleep")
async def test_check_service_health_degraded_dependency(checker: HealthCheck) -> None:
    """Test that a service with an unhealthy dependency is degraded."""
    await checker.add_service("database", AsyncMock(return_value=False))
    own_check = AsyncMock(return_value=True)
    await checker.add_service("api", own_check, depends_on=["database"])

    assert await checker.check_service_health("api") == ServiceStatus.DEGRADED
    own_check.assert_not_awaited()


# * Aggregation


@pytest.mark.anyio
async def test_check_all_services_healthy_and_cached(checker: HealthCheck) -> None:
    """Test the aggregated report and that it is cached."""
    check = AsyncMock(return_value=True)
    await checker.add_service("svc", check)

    report = await checker.check_all_services()
    cached = await checker.check_all_services()

    assert report["status"] == ServiceStatus.HEALTHY
    assert report["services"]["svc"]["status"] == ServiceStatus.HEALTHY
    assert cached is report
    check.assert_awaited_once()


@pytest.mark.anyio
async def test_check_all_services_bypasses_expired_cache(
    checker: HealthCheck,
) -> None:
    """Test that an expired cache or ``use_cache=False`` re-runs the checks."""
    check = AsyncMock(return_value=True)
    await checker.add_service("svc", check)

    await checker.check_all_services()
    await checker.check_all_services(use_cache=False)
    checker._cache_duration = timedelta(0)  # pylint: disable=protected-access
    await checker.check_all_services()

    assert check.await_count == 3


@pytest.mark.anyio
@pytest.mark.usefixtures("no_sleep")
async def test_check_all_services_degraded(checker: HealthCheck) -> None:
    """Test that an unhealthy service degrades the overall status."""
    await checker.add_service("good", AsyncMock(return_value=True))
    await checker.add_service("bad", AsyncMock(return_value=False), max_retries=1)

    report = await checker.check_all_services()

    assert report["status"] == ServiceStatus.DEGRADED
    assert report["services"]["bad"]["status"] == ServiceStatus.UNHEALTHY


@pytest.mark.anyio
async def test_check_all_services_exception(checker: HealthCheck) -> None:
    """Test that an exception while checking a service is reported."""
    await checker.add_service("svc", AsyncMock(return_value=True))

    with patch.object(
        checker, "check_service_health", AsyncMock(side_effect=RuntimeError("boom"))
    ):
        report = await checker.check_all_services()

    assert report["status"] == ServiceStatus.DEGRADED
    assert report["services"]["svc"] == {
        "status": ServiceStatus.UNHEALTHY,
        "error": "boom",
        "last_check": report["services"]["svc"]["last_check"],
    }


# * Waiting and cleanup


@pytest.mark.anyio
async def test_wait_for_services_backs_off_until_healthy(
    checker: HealthCheck, no_sleep: AsyncMock
) -> None:
    """Test that polling bypasses the cache and backs off with the elapsed time."""
    statuses = [{"status": ServiceStatus.DEGRADED}] * 3 + [
        {"status": ServiceStatus.HEALTHY}
    ]
    with (
        patch.object(
            checker, "check_all_services", AsyncMock(side_effect=statuses)
        ) as check_all,
        patch(f"{HEALTH}.time.monotonic", side_effect=[0, 5, 15, 100]),
    ):
        await checker.wait_for_services()

    check_all.assert_awaited_with(use_cache=False)
    assert [c.args[0] for c in no_sleep.await_args_list] == [1, 2, 15]


@pytest.mark.anyio
async def test_wait_for_services_is_bounded_by_caller_timeout(
    checker: HealthCheck,
) -> None:
    """Test that a caller's timeout stops waiting for services that stay unhealthy."""
    check_all = AsyncMock(return_value={"status": ServiceStatus.DEGRADED})
    with patch.object(checker, "check_all_services", check_all):
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.01):
                await checker.wait_for_services()


@pytest.mark.anyio
async def test_wait_for_services_propagates_errors(checker: HealthCheck) -> None:
    """Test that an error while checking services is not swallowed."""
    check_all = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(checker, "check_all_services", check_all):
        with pytest.raises(RuntimeError, match="boom"):
            await checker.wait_for_services()


@pytest.mark.anyio
async def test_cleanup(checker: HealthCheck) -> None:
    """Test that cleanup unregisters every service and clears the cache."""
    await checker.add_service("svc", AsyncMock(return_value=True))
    await checker.check_all_services()

    await checker.cleanup()

    report = await checker.check_all_services()
    assert report["services"] == {}
