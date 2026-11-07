"""Gmail service for sending automation response emails."""

from srcs.services.gmail.gmail_service import GmailService
from srcs.services.gmail.email_templates import EmailTemplate, EmailContext
from srcs.services.gmail.email_template_selector import EmailTemplateSelector, CommunicationEvent

__all__ = [
    "GmailService",
    "EmailTemplate",
    "EmailContext",
    "EmailTemplateSelector",
    "CommunicationEvent",
]
