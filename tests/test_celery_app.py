"""Tests for Celery app configuration."""

from src.backend.app.core.celery_app import celery_app


def test_celery_app_broker_url() -> None:
    """Test that the broker URL is a single AMQP URL string."""
    assert celery_app.conf.broker_url == "amqp://guest:guest@localhost:5672//"


def test_celery_app_result_backend() -> None:
    """Test that the result backend points to Redis."""
    assert celery_app.conf.result_backend == "redis://localhost:6379/0"


def test_celery_app_redbeat_redis_url() -> None:
    """Test that redbeat stores the schedule in the configured Redis."""
    assert celery_app.conf.redbeat_redis_url == "redis://localhost:6379/0"


def test_celery_app_soft_time_limit_below_hard_limit() -> None:
    """Test that the soft time limit fires before the hard time limit."""
    assert celery_app.conf.task_soft_time_limit < celery_app.conf.task_time_limit
