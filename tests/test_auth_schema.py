"""Tests for authentication schemas."""

from typing import Any

from fastapi import HTTPException
import pytest

from src.backend.app.auth.schema import SecurityQuestionSchema, UserCreateSchema

USER_DATA: dict[str, Any] = {
    "email": "jane@example.com",
    "first_name": "jane",
    "last_name": "doe",
    "id_no": 1,
    "security_question": SecurityQuestionSchema.BIRTH_CITY,
    "security_answer": "paris",
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            SecurityQuestionSchema.MOTHER_MAIDEN_NAME,
            "What is your mother's maiden name?",
        ),
        (
            SecurityQuestionSchema.CHILDHOOD_FRIEND,
            "What is the name of your childhood friend?",
        ),
        (SecurityQuestionSchema.FAVORITE_COLOR, "What is your favorite color?"),
        (
            SecurityQuestionSchema.BIRTH_CITY,
            "What is the name of the city you were born in?",
        ),
        ("unknown", "Unknown security question"),
    ],
)
def test_get_description(value: SecurityQuestionSchema, expected: str) -> None:
    """Test that each question has a description and unknowns fall back."""
    assert SecurityQuestionSchema.get_description(value) == expected


def test_user_create_accepts_matching_passwords() -> None:
    """Test that matching passwords validate."""
    user = UserCreateSchema(
        **USER_DATA, password="secret123", confirm_password="secret123"
    )
    assert user.confirm_password == "secret123"


def test_user_create_rejects_mismatched_passwords() -> None:
    """Test that mismatched passwords raise a 400 HTTPException."""
    data = {**USER_DATA, "password": "secret123", "confirm_password": "other1234"}
    with pytest.raises(HTTPException) as exc_info:
        UserCreateSchema(**data)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == {
        "status": "error",
        "message": "Passwords do not match.",
        "action": "Please ensure that the passwords you entered match",
    }
