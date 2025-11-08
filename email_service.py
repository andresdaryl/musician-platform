import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EMAIL_MOCK = os.getenv("EMAIL_MOCK", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@musicianplatform.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
):
    """Send email - mock implementation for development"""
    if EMAIL_MOCK:
        logger.info(f"\n{'='*80}")
        logger.info(f"MOCK EMAIL")
        logger.info(f"To: {to_email}")
        logger.info(f"From: {EMAIL_FROM}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body:\n{body}")
        if html_body:
            logger.info(f"HTML Body:\n{html_body}")
        logger.info(f"{'='*80}\n")
        return True
    else:
        # Implement actual email sending here (SendGrid, AWS SES, etc.)
        logger.error("Email sending not implemented for production")
        return False


async def send_verification_email(email: str, token: str):
    verification_url = f"{FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your email - Musician Platform"
    body = f"""
    Welcome to Musician Platform!
    
    Please verify your email address by clicking the link below:
    {verification_url}
    
    This link will expire in 48 hours.
    
    If you didn't create an account, please ignore this email.
    """
    
    await send_email(email, subject, body)


async def send_password_reset_email(email: str, token: str):
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    subject = "Reset your password - Musician Platform"
    body = f"""
    You requested a password reset for your Musician Platform account.
    
    Click the link below to reset your password:
    {reset_url}
    
    This link will expire in 24 hours.
    
    If you didn't request this, please ignore this email.
    """
    
    await send_email(email, subject, body)
