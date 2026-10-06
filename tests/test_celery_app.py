"""Tests for Celery app configuration."""

import pytest

from src.backend.app.core.celery_app import celery_app


@pytest.mark.parametrize(
    ("setting", "expected"),
    [
        ("broker_url", "amqp://guest:guest@localhost:5672//"),
        ("result_backend", "redis://localhost:6379/0"),
        ("redbeat_redis_url", "redis://localhost:6379/0"),
    ],
)
def test_celery_app_connection_urls(setting: str, expected: str) -> None:
    """Test the broker, result backend and redbeat URLs built from settings."""
    assert celery_app.conf[setting] == expected


def test_celery_app_soft_time_limit_below_hard_limit() -> None:
    """Test that the soft time limit fires before the hard time limit."""
    assert celery_app.conf.task_soft_time_limit < celery_app.conf.task_time_limit
