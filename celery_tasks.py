from celery_app import celery_app
import logging
import asyncio
from email_service import send_verification_email, send_password_reset_email

logger = logging.getLogger(__name__)


@celery_app.task(name="send_verification_email_task")
def send_verification_email_task(email: str, token: str):
    """Background task to send verification email"""
    try:
        asyncio.run(send_verification_email(email, token))
        logger.info(f"Verification email sent to {email}")
        return {"status": "success", "email": email}
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="send_password_reset_email_task")
def send_password_reset_email_task(email: str, token: str):
    """Background task to send password reset email"""
    try:
        asyncio.run(send_password_reset_email(email, token))
        logger.info(f"Password reset email sent to {email}")
        return {"status": "success", "email": email}
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="process_media_thumbnail")
def process_media_thumbnail(media_url: str):
    """Background task to generate thumbnails for media"""
    try:
        # Placeholder for thumbnail generation logic
        logger.info(f"Processing thumbnail for {media_url}")
        return {"status": "success", "media_url": media_url}
    except Exception as e:
        logger.error(f"Error processing thumbnail: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="cleanup_expired_tokens")
def cleanup_expired_tokens():
    """Background task to clean up expired tokens"""
    try:
        # This would run periodically to clean up expired verification and reset tokens
        logger.info("Cleaning up expired tokens")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error cleaning up tokens: {e}")
        return {"status": "error", "message": str(e)}
