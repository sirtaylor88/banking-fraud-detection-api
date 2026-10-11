"""Tests for the templated email base class."""

from unittest.mock import MagicMock

from jinja2 import DictLoader, Environment
import pytest

from src.backend.app.core.emails import base
from src.backend.app.core.emails.base import EmailTemplate


class WelcomeEmail(EmailTemplate):
    template_name = "welcome.html"
    template_name_plain = "welcome.txt"
    subject = "Welcome"


class MissingPlainEmail(EmailTemplate):
    template_name = "welcome.html"
    template_name_plain = ""
    subject = "Welcome"


@pytest.fixture(autouse=True)
def fixture_email_env(monkeypatch: pytest.MonkeyPatch) -> None:
    env = Environment(
        loader=DictLoader(
            {"welcome.html": "<p>Hi {{ name }}</p>", "welcome.txt": "Hi {{ name }}"}
        ),
        autoescape=True,
    )
    monkeypatch.setattr(base, "email_env", env)


@pytest.fixture(name="send_task")
def fixture_send_task(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    task = MagicMock()
    monkeypatch.setattr(base, "send_email_task", task)
    return task


@pytest.mark.parametrize(
    ("email_to", "subject_override", "recipients", "subject"),
    [
        ("a@example.com", None, ["a@example.com"], "Welcome"),
        (
            ["a@example.com", "b@example.com"],
            "Hey",
            ["a@example.com", "b@example.com"],
            "Hey",
        ),
    ],
)
async def test_send_email_queues_rendered_task(
    send_task: MagicMock,
    email_to: str | list[str],
    subject_override: str | None,
    recipients: list[str],
    subject: str,
) -> None:
    """Test that both templates are rendered and the task is queued."""
    await WelcomeEmail.send_email(email_to, {"name": "<Ann>"}, subject_override)

    send_task.delay.assert_called_once_with(
        recipients=recipients,
        subject=subject,
        html_content="<p>Hi &lt;Ann&gt;</p>",
        plain_content="Hi &lt;Ann&gt;",
    )


@pytest.mark.parametrize(
    ("email_class", "send_task_kwargs"),
    [
        (MissingPlainEmail, {}),
        (
            WelcomeEmail,
            {"delay": MagicMock(side_effect=ConnectionError("broker down"))},
        ),
    ],
)
async def test_send_email_logs_errors_without_raising(
    monkeypatch: pytest.MonkeyPatch,
    email_class: type[EmailTemplate],
    send_task_kwargs: dict[str, MagicMock],
) -> None:
    """Test that a template or queueing error is logged, not raised."""
    send_task = MagicMock(**send_task_kwargs)
    monkeypatch.setattr(base, "send_email_task", send_task)
    logger = MagicMock()
    monkeypatch.setattr(base, "logger", logger)

    await email_class.send_email("a@example.com", {"name": "Ann"})

    logger.error.assert_called_once()
