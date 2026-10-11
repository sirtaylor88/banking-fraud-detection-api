"""Celery tasks that send emails.

Attributes:
    logger (Logger): Module logger.
"""

import asyncio
from typing import TYPE_CHECKING, Any

from fastapi_mail import MessageSchema, MessageType, MultipartSubtypeEnum

from src.backend.app.core.celery_app import celery_app
from src.backend.app.core.emails.config import mail_client
from src.backend.app.core.logging import get_logger

if TYPE_CHECKING:
    from celery import Task

logger = get_logger()


@celery_app.task(
    name="send_email_task",
    bind=True,
    max_retries=3,
    soft_time_limit=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_email_task(
    self: "Task[Any, bool]",
    *,
    recipients: list[str],
    subject: str,
    html_content: str,
    plain_content: str,
) -> bool:
    """Send a multipart HTML/plain-text email.

    Failures are logged and re-raised so that Celery retries the task
    (``autoretry_for``) with exponential back-off.

    Args:
        self (Task[Any, bool]): Bound Celery task instance.
        recipients (list[str]): Recipient email addresses.
        subject (str): Email subject.
        html_content (str): Rendered HTML body.
        plain_content (str): Rendered plain-text alternative body.

    Returns:
        bool: ``True`` once the email has been sent.

    Raises:
        Exception: Any error raised while building or sending the message.
    """
    try:
        # Validate from a dict so pydantic coerces the address strings
        # into ``NameEmail`` objects.
        message = MessageSchema.model_validate(
            {
                "subject": subject,
                "recipients": recipients,
                "body": html_content,
                "subtype": MessageType.html,
                "alternative_body": plain_content,
                "multipart_subtype": MultipartSubtypeEnum.alternative,
            }
        )
        asyncio.run(mail_client.send_message(message))
        logger.info(f"Email successfully sent to {recipients} with subject {subject}")

        return True

    except Exception as exc:
        logger.error(f"Failed to send email to {recipients}: {exc}")
        raise
