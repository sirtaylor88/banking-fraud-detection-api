"""Tests for the email Celery tasks."""

from unittest.mock import AsyncMock, MagicMock

from fastapi_mail import MessageType
import pytest

from src.backend.app.core.emails import tasks
from src.backend.app.core.emails.tasks import send_email_task

EMAIL_KWARGS = {
    "recipients": ["user@example.com"],
    "subject": "Hello",
    "html_content": "<p>Hi</p>",
    "plain_content": "Hi",
}


@pytest.fixture(name="mail_client")
def fixture_mail_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock(send_message=AsyncMock())
    monkeypatch.setattr(tasks, "mail_client", client)
    return client


def test_send_email_task_sends_multipart_message(mail_client: MagicMock) -> None:
    """Test that the task sends an HTML message with a plain-text alternative."""
    assert send_email_task.run(**EMAIL_KWARGS) is True

    message = mail_client.send_message.await_args.args[0]
    assert message.subject == "Hello"
    assert [r.email for r in message.recipients] == ["user@example.com"]
    assert message.body == "<p>Hi</p>"
    assert message.alternative_body == "Hi"
    assert message.subtype == MessageType.html


def test_send_email_task_reraises_errors(mail_client: MagicMock) -> None:
    """Test that a sending error is re-raised so Celery retries the task."""
    mail_client.send_message.side_effect = ConnectionError("SMTP down")

    with pytest.raises(ConnectionError, match="SMTP down"):
        send_email_task.run(**EMAIL_KWARGS)
