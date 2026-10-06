"""Tests for the main FastAPI application."""

import asyncio
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from src.backend.app.core.config import settings
from src.backend.app.core.health import ServiceStatus
from src.backend.app.main import app, shutdown

WAIT_FOR_SERVICES = "src.backend.app.main.health_checker.wait_for_services"
CHECK_ALL_SERVICES = "src.backend.app.main.health_checker.check_all_services"


@pytest.fixture(name="mock_startup")
def fixture_mock_startup() -> Iterator[dict[str, AsyncMock]]:
    """Patch external dependencies used by the lifespan.

    Yields:
        dict[str, AsyncMock]: The mocks, keyed by name.
    """
    with (
        patch("src.backend.app.main.init_db", new_callable=AsyncMock) as init_db,
        patch(WAIT_FOR_SERVICES, new_callable=AsyncMock) as wait,
        patch("src.backend.app.main.shutdown", new_callable=AsyncMock) as shutdown_mock,
    ):
        yield {
            "init_db": init_db,
            "wait_for_services": wait,
            "shutdown": shutdown_mock,
        }


def test_home(mock_startup: dict[str, AsyncMock]) -> None:
    """Test the home endpoint returns a welcome message."""
    with TestClient(app) as client:
        response = client.get(f"{settings.API_V1_STR}/home/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to NextGen Bank - FastAPI!"}

    mock_startup["init_db"].assert_awaited_once()
    mock_startup["wait_for_services"].assert_awaited_once()
    mock_startup["shutdown"].assert_awaited_once()


async def _never_healthy() -> None:
    """Wait longer than the patched startup timeout."""
    await asyncio.sleep(1)


def test_lifespan_fails_when_services_unhealthy(
    mock_startup: dict[str, AsyncMock],
) -> None:
    """Test that startup aborts and cleans up when services stay unhealthy."""
    mock_startup["wait_for_services"].side_effect = _never_healthy

    with patch("src.backend.app.main.STARTUP_TIMEOUT", 0.01):
        with pytest.raises(RuntimeError, match="Critical services failed to start"):
            with TestClient(app):
                pass  # pragma: no cover

    mock_startup["shutdown"].assert_awaited_once()


@pytest.mark.anyio
async def test_shutdown_releases_resources() -> None:
    """Test that shutdown clears the health checker, registry and engine."""
    registry = AsyncMock()
    with (
        patch("src.backend.app.main.health_checker.cleanup") as cleanup,
        patch("src.backend.app.main.engine") as engine,
    ):
        engine.dispose = AsyncMock()
        await shutdown(registry)

    cleanup.assert_awaited_once()
    registry.aclose.assert_awaited_once()
    engine.dispose.assert_awaited_once()


@pytest.mark.parametrize(
    ("mock_kwargs", "expected_code", "expected_body"),
    [
        pytest.param(
            {"return_value": {"status": status, "services": {}}},
            code,
            {"status": status, "services": {}},
            id=status,
        )
        for status, code in [
            (ServiceStatus.HEALTHY, 200),
            (ServiceStatus.DEGRADED, 206),
            (ServiceStatus.UNHEALTHY, 503),
        ]
    ]
    + [
        pytest.param(
            {"side_effect": RuntimeError("boom")},
            500,
            {"status": ServiceStatus.UNHEALTHY, "error": "boom"},
            id="error",
        )
    ],
)
def test_health_endpoint(
    mock_kwargs: dict[str, Any],
    expected_code: int,
    expected_body: dict[str, object],
) -> None:
    """Test that the health endpoint maps the report or a failure to an HTTP code."""
    with patch(CHECK_ALL_SERVICES, new_callable=AsyncMock, **mock_kwargs):
        response = TestClient(app).get("/health")

    assert response.status_code == expected_code
    assert response.json() == expected_body
