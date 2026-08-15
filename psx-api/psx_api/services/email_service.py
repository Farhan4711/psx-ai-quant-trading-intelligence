"""
Email service.

In development (no SMTP configured): logs the email body to structlog so
the developer can see verification links directly in the console.
In production: sends via SMTP using aiosmtplib.
"""

from __future__ import annotations

import structlog

from psx_api.config import settings

logger = structlog.get_logger(__name__)


async def send_verification_email(email: str, token: str) -> None:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    subject = "Verify your PSX AI account"
    body = (
        f"Hi,\n\nPlease verify your email address by clicking the link below:\n\n"
        f"{link}\n\nThis link expires in 24 hours.\n\nPSX AI Trading Intelligence"
    )
    await _send(email, subject, body)
    logger.info("Verification email dispatched", email=email)


async def send_password_reset_email(email: str, token: str) -> None:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    subject = "Reset your PSX AI password"
    body = (
        f"Hi,\n\nClick the link below to reset your password:\n\n"
        f"{link}\n\nThis link expires in 1 hour. If you did not request this, ignore it.\n\n"
        f"PSX AI Trading Intelligence"
    )
    await _send(email, subject, body)
    logger.info("Password reset email dispatched", email=email)


async def _send(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        # Dev mode: log instead of sending
        logger.info(
            "EMAIL (dev — not sent)",
            to=to,
            subject=subject,
            body=body,
        )
        return

    from email.mime.text import MIMEText

    import aiosmtplib

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = settings.smtp_from_email
    msg["To"] = to
    msg["Subject"] = subject

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        use_tls=settings.smtp_use_tls,
    )
