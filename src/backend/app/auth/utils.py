"""Authentication helpers: OTP and username generation, password hashing."""

import secrets
import string
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.backend.app.core.config import settings

# * Shared Argon2 hasher with the library's default parameters.
_ph: Final[PasswordHasher] = PasswordHasher()


def generate_otp(length: int = 6) -> str:
    """Generate a numeric one-time password.

    Args:
        length (int): Number of digits in the OTP. Defaults to 6.

    Returns:
        str: A string of ``length`` random digits, e.g. ``"482915"``.
    """
    # * secrets, not random: OTPs must not be predictable.
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_password_hash(password: str) -> str:
    """Hash a plain-text password with Argon2.

    Args:
        password (str): The plain-text password to hash.

    Returns:
        str: The encoded Argon2 hash, including its salt and parameters.
    """
    return _ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Check a plain-text password against an Argon2 hash.

    Args:
        password (str): The plain-text password to check.
        hashed_password (str): The encoded Argon2 hash to check it against.

    Returns:
        bool: ``True`` if the password matches the hash, ``False`` otherwise.
    """
    try:
        return _ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def generate_username() -> str:
    """Generate a 12-character username prefixed with the bank's initials.

    The prefix is the uppercased first letter of each word in
    ``settings.SITE_NAME``, followed by a hyphen and random uppercase letters
    and digits filling the rest of the 12 characters.

    Returns:
        str: The username, e.g. ``"NB-A1B2C3D4E"`` for the site name
        ``"NextGen Bank"``.
    """
    bank_name = settings.SITE_NAME
    words = bank_name.split()
    prefix = "".join([word[0] for word in words]).upper()
    remaining_length = 12 - len(prefix) - 1
    alphanumeric = string.ascii_uppercase + string.digits
    random_string = "".join(
        secrets.choice(alphanumeric) for _ in range(remaining_length)
    )

    return f"{prefix}-{random_string}"
