"""SQLModel table models for authentication."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import computed_field
from sqlalchemy import func, text
from sqlalchemy.dialects import postgresql as pg
from sqlmodel import Column, Field

from src.backend.app.auth.schema import BaseUserSchema, RoleChoicesSchema


class User(BaseUserSchema, table=True):
    """Persisted user account, with credentials, OTP and lockout tracking."""

    id: UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True), default_factory=uuid4
    )
    hashed_password: str
    failed_login_attempts: int = Field(default=0, sa_type=pg.SMALLINT)
    last_failed_login: datetime | None = Field(
        default=None,
        sa_column=Column(
            pg.TIMESTAMP(
                timezone=True,
            )
        ),
    )
    otp: str = Field(max_length=6, default="")
    otp_expiry_time: datetime | None = Field(
        default=None,
        sa_column=Column(
            pg.TIMESTAMP(
                timezone=True,
            )
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(
                timezone=True,
            ),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(
                timezone=True,
            ),
            nullable=False,
            onupdate=func.current_timestamp,
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def full_name(self) -> str:
        """Return the user's full name in title case.

        Returns:
            str: First, middle (if any) and last name joined by spaces.
        """
        full_name = (
            f"{self.first_name} "
            f"{self.middle_name + ' ' if self.middle_name else ''}"
            f"{self.last_name}"
        )
        return full_name.title().strip()

    def has_role(self, role: RoleChoicesSchema) -> bool:
        """Check whether the user holds the given role.

        Args:
            role (RoleChoicesSchema): The role to compare against.

        Returns:
            bool: ``True`` if the user's role matches ``role``.
        """
        return self.role == role
