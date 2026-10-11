"""Tests for authentication helpers."""

import re

import pytest

from src.backend.app.auth import utils
from src.backend.app.auth.utils import (
    generate_otp,
    generate_password_hash,
    generate_username,
    verify_password,
)


@pytest.mark.parametrize("length", [4, 6, 8])
def test_generate_otp_returns_digits_of_given_length(length: int) -> None:
    """Test that the OTP has the requested number of digits."""
    otp = generate_otp(length)

    assert len(otp) == length
    assert otp.isdigit()


def test_generate_otp_defaults_to_six_digits() -> None:
    """Test that the OTP has 6 digits by default."""
    assert re.fullmatch(r"\d{6}", generate_otp())


def test_generate_password_hash_is_salted_argon2() -> None:
    """Test that hashing gives an Argon2 hash with a fresh salt each time."""
    first = generate_password_hash("s3cret")

    assert first.startswith("$argon2")
    assert first != "s3cret"
    assert first != generate_password_hash("s3cret")


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [("s3cret", True), ("wrong", False)],
)
def test_verify_password(candidate: str, expected: bool) -> None:
    """Test that only the original password verifies against its hash."""
    hashed = generate_password_hash("s3cret")

    assert verify_password(candidate, hashed) is expected


@pytest.mark.parametrize(
    ("site_name", "prefix"),
    [("NextGen Bank", "NB"), ("first national bank", "FNB"), ("Bank", "B")],
)
def test_generate_username_uses_site_initials(
    monkeypatch: pytest.MonkeyPatch, site_name: str, prefix: str
) -> None:
    """Test that usernames are 12 characters: initials, hyphen, random suffix."""
    monkeypatch.setattr(utils.settings, "SITE_NAME", site_name)

    username = generate_username()

    assert len(username) == 12
    assert re.fullmatch(rf"{prefix}-[A-Z0-9]{{{11 - len(prefix)}}}", username)
