"""Tests for authentication table models."""

import pytest

from src.backend.app.auth.models import User
from src.backend.app.auth.schema import RoleChoicesSchema, SecurityQuestionSchema


def make_user(**overrides: object) -> User:
    """Build a User with valid defaults.

    Args:
        **overrides (object): Field values replacing the defaults.

    Returns:
        User: The user instance.
    """
    data: dict[str, object] = {
        "email": "jane@example.com",
        "first_name": "jane",
        "last_name": "doe",
        "id_no": 1,
        "security_question": SecurityQuestionSchema.BIRTH_CITY,
        "security_answer": "paris",
        "hashed_password": "hashed",
        **overrides,
    }
    return User(**data)


@pytest.mark.parametrize(
    ("middle_name", "expected"),
    [(None, "Jane Doe"), ("", "Jane Doe"), ("marie", "Jane Marie Doe")],
)
def test_full_name(middle_name: str | None, expected: str) -> None:
    """Test that the full name is title-cased and skips a missing middle name."""
    assert make_user(middle_name=middle_name).full_name == expected


@pytest.mark.parametrize(
    ("role", "expected"),
    [(RoleChoicesSchema.ADMIN, True), (RoleChoicesSchema.TELLER, False)],
)
def test_has_role(role: RoleChoicesSchema, expected: bool) -> None:
    """Test that has_role matches only the user's own role."""
    assert make_user(role=RoleChoicesSchema.ADMIN).has_role(role) is expected


def test_timestamps_are_timezone_aware() -> None:
    """Test that created_at and updated_at default to aware datetimes."""
    user = make_user()
    assert user.created_at.tzinfo is not None
    assert user.updated_at.tzinfo is not None
