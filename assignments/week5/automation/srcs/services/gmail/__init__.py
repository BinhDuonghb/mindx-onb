"""Gmail service for sending automation response emails."""

from srcs.services.gmail.gmail_service import GmailService
from srcs.services.gmail.email_templates import EmailTemplate, EmailContext

__all__ = ["GmailService", "EmailTemplate", "EmailContext"]
