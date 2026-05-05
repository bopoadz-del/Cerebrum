"""
Email Service

Sends transactional emails (welcome, password reset, verification) via SMTP.
Falls back to logging when SMTP is not configured (USE_STUB_NOTIFICATIONS=true).
Provides both sync and async send helpers.
"""

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _build_message(
    to_email: Union[str, List[str]],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> MIMEMultipart:
    recipients = [to_email] if isinstance(to_email, str) else to_email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


def _send_smtp(to_email: str, subject: str, html_body: str) -> None:
    """Send email via SMTP. Raises on failure."""
    msg = _build_message(to_email, subject, html_body)
    recipients = [to_email] if isinstance(to_email, str) else [to_email]

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_TLS:
            server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, recipients, msg.as_string())


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email synchronously. Returns True on success, False on failure.

    If SMTP is not configured or USE_STUB_NOTIFICATIONS is true, logs the
    email instead of sending it.
    """
    if settings.USE_STUB_NOTIFICATIONS or not _smtp_configured():
        logger.info(
            "EMAIL STUB",
            extra={"to": to_email, "subject": subject},
        )
        return True
    try:
        _send_smtp(to_email, subject, html_body)
        logger.info("Email sent", extra={"to": to_email, "subject": subject})
        return True
    except Exception as exc:
        logger.error("Failed to send email", extra={"to": to_email, "error": str(exc)})
        return False


def send_welcome_email(to_email: str, full_name: Optional[str] = None) -> bool:
    name = full_name or to_email.split("@")[0]
    subject = "Welcome to Cerebrum AI"
    html = f"""
    <html><body>
    <h2>Welcome to Cerebrum AI, {name}!</h2>
    <p>Your account has been created successfully.</p>
    <p>Log in at <a href="{settings.FRONTEND_URL}">{settings.FRONTEND_URL}</a></p>
    </body></html>
    """
    return send_email(to_email, subject, html)


def send_verification_email(to_email: str, token: str, full_name: Optional[str] = None) -> bool:
    name = full_name or to_email.split("@")[0]
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your Cerebrum AI email"
    html = f"""
    <html><body>
    <h2>Hi {name}, please verify your email</h2>
    <p>Click the link below to verify your email address (expires in 24 hours):</p>
    <p><a href="{verify_url}">Verify Email</a></p>
    <p>If you did not sign up, ignore this email.</p>
    </body></html>
    """
    return send_email(to_email, subject, html)


def send_password_reset_email(to_email: str, token: str, full_name: Optional[str] = None) -> bool:
    name = full_name or to_email.split("@")[0]
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Reset your Cerebrum AI password"
    html = f"""
    <html><body>
    <h2>Hi {name}, here is your password reset link</h2>
    <p>Click the link below to reset your password (expires in 1 hour):</p>
    <p><a href="{reset_url}">Reset Password</a></p>
    <p>If you did not request a reset, ignore this email.</p>
    </body></html>
    """
    return send_email(to_email, subject, html)


def send_invitation_email(
    to_email: str,
    inviter_name: str,
    organization: str,
    invite_token: str,
) -> bool:
    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={invite_token}"
    subject = f"{inviter_name} invited you to {organization}"
    html = f"""
    <html><body>
    <h2>You're invited!</h2>
    <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization}</strong>
    on Cerebrum AI.</p>
    <p><a href="{invite_url}">Accept Invitation</a></p>
    <p>This link expires in 7 days. If you were not expecting this, ignore it.</p>
    </body></html>
    """
    return send_email(to_email, subject, html)


# ---------------------------------------------------------------------------
# Async wrappers (use in async FastAPI route handlers)
# ---------------------------------------------------------------------------

async def async_send_welcome_email(to_email: str, full_name: Optional[str] = None) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_welcome_email, to_email, full_name)


async def async_send_verification_email(
    to_email: str, token: str, full_name: Optional[str] = None
) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_verification_email, to_email, token, full_name)


async def async_send_password_reset_email(
    to_email: str, token: str, full_name: Optional[str] = None
) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_password_reset_email, to_email, token, full_name)


async def async_send_invitation_email(
    to_email: str,
    inviter_name: str,
    organization: str,
    invite_token: str,
) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, send_invitation_email, to_email, inviter_name, organization, invite_token
    )
