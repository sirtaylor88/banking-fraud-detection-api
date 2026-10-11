"""Email connection settings and the shared FastMail client.

The connection targets the local SMTP server (Mailpit in Docker Compose),
which needs neither credentials, TLS nor certificate validation.

Attributes:
    TEMPLATES_DIR (Path): Folder holding the Jinja email templates.
    email_conf (ConnectionConfig): SMTP connection settings built from
        ``settings``.
    mail_client (FastMail): Client used to send emails.
"""

from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail
from pydantic import SecretStr

from src.backend.app.core.config import settings

TEMPLATES_DIR: Path = Path(__file__).parent / "templates"

email_conf: ConnectionConfig = ConnectionConfig(
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_USERNAME="",
    MAIL_PASSWORD=SecretStr(""),
    MAIL_SSL_TLS=False,
    MAIL_STARTTLS=False,
    USE_CREDENTIALS=False,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=TEMPLATES_DIR,
)

mail_client: FastMail = FastMail(email_conf)
