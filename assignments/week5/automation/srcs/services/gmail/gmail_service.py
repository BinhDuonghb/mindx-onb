"""Gmail SMTP service for sending automation response emails."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from srcs.config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
from srcs.services.gmail.email_templates import EmailContext, EmailTemplateRenderer

logger = logging.getLogger(__name__)


class GmailService:
    """Service for sending emails via Gmail SMTP.

    Handles:
    - SMTP connection setup and teardown
    - Email template rendering and composition
    - Email delivery with error handling and retry logic
    - Logging of all email operations

    Example:
        service = GmailService()
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot login",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
            employee_name="John Doe",
        )
        success = service.send_email(context)
    """

    def __init__(
        self,
        smtp_host: str = SMTP_HOST,
        smtp_port: int = SMTP_PORT,
        smtp_username: str = SMTP_USERNAME,
        smtp_password: str = SMTP_PASSWORD,
        from_email: str = SMTP_FROM_EMAIL,
    ):
        """Initialize Gmail SMTP service.

        Args:
            smtp_host: SMTP server hostname (default: smtp.gmail.com)
            smtp_port: SMTP server port (default: 587 for TLS)
            smtp_username: SMTP username/email
            smtp_password: SMTP password (app-specific password for Gmail)
            from_email: From email address

        Raises:
            ValueError: If required credentials are missing
        """
        if not all([smtp_username, smtp_password, from_email]):
            raise ValueError(
                "Missing required SMTP credentials. "
                "Set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL."
            )

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email

        logger.info(f"Gmail service initialized: {smtp_username}@{smtp_host}:{smtp_port}")

    def send_email(
        self,
        context: EmailContext,
        max_retries: int = 3,
    ) -> bool:
        """Send an email based on template context.

        Args:
            context: Email context with template and data
            max_retries: Maximum number of retry attempts

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Render email template
            subject, body = EmailTemplateRenderer.render(context)

            logger.debug(
                f"Sending email to {context.recipient_email} "
                f"(ticket {context.ticket_id}, template {context.template})"
            )

            # Send with retry logic
            for attempt in range(max_retries):
                try:
                    self._send_smtp(
                        to_email=context.recipient_email,
                        subject=subject,
                        body=body,
                    )

                    logger.info(
                        f"Email sent successfully to {context.recipient_email} "
                        f"(ticket {context.ticket_id}, template {context.template})"
                    )
                    return True

                except smtplib.SMTPAuthenticationError as e:
                    logger.error(f"SMTP authentication failed: {str(e)}")
                    return False

                except smtplib.SMTPException as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"SMTP error on attempt {attempt + 1}/{max_retries}: {str(e)}. "
                            f"Retrying..."
                        )
                        continue
                    else:
                        logger.error(
                            f"SMTP error after {max_retries} attempts: {str(e)}"
                        )
                        return False

                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Error on attempt {attempt + 1}/{max_retries}: {str(e)}. "
                            f"Retrying..."
                        )
                        continue
                    else:
                        logger.error(
                            f"Failed to send email after {max_retries} attempts: {str(e)}"
                        )
                        return False

        except ValueError as e:
            logger.error(f"Invalid email context: {str(e)}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False

        return False

    def _send_smtp(self, to_email: str, subject: str, body: str) -> None:
        """Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)

        Raises:
            smtplib.SMTPException: On SMTP errors
            Exception: On other errors
        """
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        # Attach plain text body
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            # Enable TLS encryption
            server.starttls()

            # Authenticate
            server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.send_message(msg)

            logger.debug(f"Email delivered via SMTP to {to_email}")

    def validate_connection(self) -> bool:
        """Validate SMTP connection and credentials.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.debug("Validating SMTP connection...")

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)

            logger.info("SMTP connection validated successfully")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            return False

        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection failed: {str(e)}")
            return False

        except Exception as e:
            logger.error(f"Failed to validate SMTP connection: {str(e)}")
            return False
