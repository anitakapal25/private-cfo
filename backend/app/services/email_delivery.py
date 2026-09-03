"""Minimal transactional email boundary; never logs recipients or challenge secrets."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlencode

from app.core.config import Settings


class EmailDeliveryUnavailableError(RuntimeError):
    pass


class TransactionalEmailDelivery(Protocol):
    async def send_verification(self, recipient: str, token: str) -> None: ...
    async def send_password_reset(self, recipient: str, token: str) -> None: ...


class DisabledEmailDelivery:
    async def send_verification(self, recipient: str, token: str) -> None:
        del recipient, token
        raise EmailDeliveryUnavailableError("Email delivery is not configured")

    async def send_password_reset(self, recipient: str, token: str) -> None:
        del recipient, token
        raise EmailDeliveryUnavailableError("Email delivery is not configured")


class SmtpEmailDelivery:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_verification(self, recipient: str, token: str) -> None:
        await self._send(recipient, "Verify your Artha email", "/verify-email", token)

    async def send_password_reset(self, recipient: str, token: str) -> None:
        await self._send(recipient, "Reset your Artha password", "/reset-password", token)

    async def _send(self, recipient: str, subject: str, path: str, token: str) -> None:
        app_url = (self.settings.public_app_url or "").rstrip("/")
        link = f"{app_url}{path}?{urlencode({'token': token})}"
        message = EmailMessage()
        message["From"] = self.settings.email_from_address
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(f"Use this single-use link within 30 minutes:\n{link}\n\nIf you did not request this, you can ignore this email.")
        await asyncio.to_thread(self._deliver, message)

    def _deliver(self, message: EmailMessage) -> None:
        try:
            smtp_client = (
                smtplib.SMTP_SSL
                if self.settings.smtp_security == "ssl"
                else smtplib.SMTP
            )
            with smtp_client(
                self.settings.smtp_host, self.settings.smtp_port, timeout=10
            ) as client:
                if self.settings.smtp_security == "starttls":
                    client.ehlo()
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                client.login(self.settings.smtp_username, self.settings.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryUnavailableError("Transactional email could not be delivered") from exc


def get_email_delivery(settings: Settings) -> TransactionalEmailDelivery:
    if settings.email_delivery_mode == "smtp":
        return SmtpEmailDelivery(settings)
    return DisabledEmailDelivery()
