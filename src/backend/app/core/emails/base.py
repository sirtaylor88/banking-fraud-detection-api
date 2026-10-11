"""Base class for templated emails.

Attributes:
    logger (Logger): Module logger.
    email_env (Environment): Jinja environment loading templates from
        ``TEMPLATES_DIR`` with autoescaping enabled.
"""

from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.backend.app.core.emails.config import TEMPLATES_DIR
from src.backend.app.core.emails.tasks import send_email_task
from src.backend.app.core.logging import get_logger

logger = get_logger()

email_env: Environment = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)


class EmailTemplate:
    """Base class for an email rendered from an HTML and a plain-text template.

    Subclasses set the class attributes and call :meth:`send_email`.

    Attributes:
        template_name (str): HTML template file, relative to ``TEMPLATES_DIR``.
        template_name_plain (str): Plain-text template file, relative to
            ``TEMPLATES_DIR``.
        subject (str): Default email subject.
    """

    template_name: str
    template_name_plain: str
    subject: str

    @classmethod
    async def send_email(
        cls,
        email_to: str | list[str],
        context: dict[str, Any],
        subject_override: str | None = None,
    ) -> None:
        """Render both templates and queue the email for sending.

        Errors are logged, not raised, so a failed email never breaks the
        caller's request.

        Args:
            email_to (str | list[str]): One recipient address or a list of them.
            context (dict[str, Any]): Variables passed to both templates.
            subject_override (str | None): Subject to use instead of
                ``subject``.
        """
        recipients_list: list[str] = (
            [email_to] if isinstance(email_to, str) else email_to
        )
        try:
            if not cls.template_name or not cls.template_name_plain:
                raise ValueError(
                    "Both HTML and plain text email template are required."
                )

            html_template = email_env.get_template(cls.template_name)
            plain_template = email_env.get_template(cls.template_name_plain)

            html_content = html_template.render(**context)
            plain_content = plain_template.render(**context)

            task = send_email_task.delay(
                recipients=recipients_list,
                subject=subject_override or cls.subject,
                html_content=html_content,
                plain_content=plain_content,
            )

            logger.info(f"Email task {task.id} queued for: {recipients_list}")

        except Exception as exc:
            logger.error(f"Failed to queue email task for {recipients_list}: {exc}")
