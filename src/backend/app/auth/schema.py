"""Pydantic/SQLModel schemas and enums for user authentication."""

from enum import StrEnum

from fastapi import HTTPException, status
from pydantic import EmailStr, ValidationInfo, field_validator
from sqlmodel import Field, SQLModel


class SecurityQuestionSchema(StrEnum):
    """Security questions a user can pick for account recovery."""

    MOTHER_MAIDEN_NAME = "mother_maiden_name"
    CHILDHOOD_FRIEND = "childhood_friend"
    FAVORITE_COLOR = "favorite_color"
    BIRTH_CITY = "birth_city"

    @classmethod
    def get_description(cls, value: "SecurityQuestionSchema") -> str:
        """Return the human-readable question for a security question value.

        Args:
            value (SecurityQuestionSchema): The security question to describe.

        Returns:
            str: The question text, or ``"Unknown security question"`` if
            ``value`` has no description.
        """
        description: dict[SecurityQuestionSchema, str] = {
            cls.MOTHER_MAIDEN_NAME: "What is your mother's maiden name?",
            cls.CHILDHOOD_FRIEND: "What is the name of your childhood friend?",
            cls.FAVORITE_COLOR: "What is your favorite color?",
            cls.BIRTH_CITY: "What is the name of the city you were born in?",
        }

        return description.get(value, "Unknown security question")


class AccountStatusSchema(StrEnum):
    """Lifecycle status of a user account."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"


class RoleChoicesSchema(StrEnum):
    """Roles a user can hold within the bank."""

    CUSTOMER = "customer"
    ACCOUNT_EXECUTIVE = "account_executive"
    BRANCH_MANAGER = "branch_manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    TELLER = "teller"


class BaseUserSchema(SQLModel):
    """Fields shared by every user representation (table model and payloads)."""

    username: str | None = Field(default=None, max_length=12, unique=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    first_name: str = Field(max_length=30)
    middle_name: str | None = Field(max_length=30, default=None)
    last_name: str = Field(max_length=30)
    id_no: int = Field(unique=True, gt=0)
    is_active: bool = False
    is_superuser: bool = False
    security_question: SecurityQuestionSchema = Field(max_length=30)
    security_answer: str = Field(max_length=30)
    account_status: AccountStatusSchema = Field(default=AccountStatusSchema.INACTIVE)
    role: RoleChoicesSchema = Field(default=RoleChoicesSchema.CUSTOMER)


class UserCreateSchema(BaseUserSchema):
    """Payload for registering a new user, with password confirmation."""

    password: str = Field(min_length=8, max_length=40)
    confirm_password: str = Field(min_length=8, max_length=40)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info: ValidationInfo) -> str:
        """Check that ``confirm_password`` matches ``password``.

        Args:
            v (str): The submitted ``confirm_password`` value.
            info (ValidationInfo): Validation context holding the fields
                validated so far.

        Returns:
            str: The unchanged ``confirm_password`` value.

        Raises:
            HTTPException: 400 if the two passwords differ.
        """
        if "password" in info.data and v != info.data["password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Passwords do not match.",
                    "action": "Please ensure that the passwords you entered match",
                },
            )
        return v
