"""Tests for settings-derived URLs."""

import pytest

from src.backend.app.core.config import Settings


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "postgresql+asyncpg://test:test@localhost:5432/test"),
        (
            {"POSTGRES_HOST": "db.internal", "POSTGRES_PORT": "6543"},
            "postgresql+asyncpg://test:test@db.internal:6543/test",
        ),
        (
            {"POSTGRES_PASSWORD": "p@ss:w/rd%"},
            "postgresql+asyncpg://test:p%40ss%3Aw%2Frd%25@localhost:5432/test",
        ),
    ],
)
def test_database_url(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, str], expected: str
) -> None:
    """Test that DATABASE_URL follows POSTGRES_* env vars and escapes the password."""
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)

    assert Settings(_env_file=None).DATABASE_URL == expected  # type: ignore[call-arg]
