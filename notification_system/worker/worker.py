import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any
from celery import Celery

# Celery configuration
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
celery = Celery("notification", broker=redis_url, backend=redis_url)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMTP configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))


@celery.task(name="worker.send_email_task")
def send_email_task(
    to_email: str, subject: str, body: str, from_email: str = "noreply@example.com"
) -> Any:
    """
    Celery task to send email asynchronously
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        # Add body to email
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server (MailHog)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            # MailHog doesn't require authentication
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email} with subject '{subject}'")
        return {
            "status": "success",
            "message": f"Email sent to {to_email}",
            "subject": subject,
        }

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Start the worker
    celery.start()
