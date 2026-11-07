"""EmailTemplateSelector - Centralized email template selection based on communication events."""

from enum import Enum
from typing import Optional
from srcs.services.gmail import EmailTemplate


class CommunicationEvent(str, Enum):
    """Communication events that trigger customer emails."""

    TICKET_RECEIVED = "ticket_received"
    INVESTIGATION_IN_PROGRESS = "investigation_in_progress"
    REACTIVATION_SUCCESSFUL = "reactivation_successful"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    SYSTEM_ERROR = "system_error"
    FOLLOW_UP_REMINDER = "follow_up_reminder"


class EmailTemplateSelector:
    """Select appropriate email template based on communication event.

    Pure function-like service with no side effects.
    Maps communication events to Week 4-aligned email templates.

    Usage:
        template = EmailTemplateSelector.select(CommunicationEvent.TICKET_RECEIVED)
        if template:
            context = EmailContext(..., template=template)
            email_service.send_email(context)
    """

    TEMPLATE_MAPPING = {
        CommunicationEvent.TICKET_RECEIVED: EmailTemplate.ACKNOWLEDGEMENT,
        CommunicationEvent.INVESTIGATION_IN_PROGRESS: EmailTemplate.INVESTIGATION_UPDATE,
        CommunicationEvent.REACTIVATION_SUCCESSFUL: EmailTemplate.RESOLUTION,
        CommunicationEvent.MANUAL_REVIEW_REQUIRED: EmailTemplate.MANUAL_REVIEW,
        CommunicationEvent.SYSTEM_ERROR: EmailTemplate.SYSTEM_ERROR,
        CommunicationEvent.FOLLOW_UP_REMINDER: EmailTemplate.FOLLOW_UP,
    }

    @staticmethod
    def select(event: Optional[CommunicationEvent]) -> Optional[EmailTemplate]:
        """Select email template for a communication event.

        Pure function - no side effects, fully deterministic.

        Args:
            event: CommunicationEvent to select template for

        Returns:
            EmailTemplate enum value if event is recognized, None otherwise

        Examples:
            >>> EmailTemplateSelector.select(CommunicationEvent.TICKET_RECEIVED)
            <EmailTemplate.ACKNOWLEDGEMENT: 'acknowledgement'>

            >>> EmailTemplateSelector.select(None)
            None

            >>> EmailTemplateSelector.select("unknown")
            None
        """
        if event is None:
            return None

        return EmailTemplateSelector.TEMPLATE_MAPPING.get(event)
