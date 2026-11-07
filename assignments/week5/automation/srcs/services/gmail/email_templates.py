"""Email templates and rendering context for automation responses - Week 4 aligned."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EmailTemplate(str, Enum):
    """Email template types following Week 4 support communication structure."""

    ACKNOWLEDGEMENT = "acknowledgement"
    INVESTIGATION_UPDATE = "investigation_update"
    RESOLUTION = "resolution"
    MANUAL_REVIEW = "manual_review"
    FOLLOW_UP = "follow_up"
    SYSTEM_ERROR = "system_error"


@dataclass
class EmailContext:
    """Context data for email template rendering.

    Public fields only - sensitive HR data excluded from customer emails.
    """

    recipient_email: str
    recipient_name: str
    ticket_id: int
    ticket_title: str
    template: EmailTemplate

    # Optional fields for template customization
    action_summary: Optional[str] = None
    next_steps: Optional[str] = None
    next_update_at: Optional[str] = None
    support_email: str = "support@company.com"


class EmailTemplateRenderer:
    """Renders email content from templates and context following Week 4 standards."""

    TEMPLATES = {
        EmailTemplate.ACKNOWLEDGEMENT: {
            "subject": "RE: {ticket_title} - Ticket #{ticket_id}",
            "body": """Dear {recipient_name},

Thank you for contacting us. We have received your support request and understand this may be urgent for you.

We will investigate your request and account information to determine the best course of action. Our team typically completes initial investigations within 24 hours.

Ticket ID: {ticket_id}
Issue: {ticket_title}

We will keep you updated on progress. If you have any additional information, please reply to this email.

Best regards,
Support Team
{support_email}""",
        },
        EmailTemplate.INVESTIGATION_UPDATE: {
            "subject": "Update: {ticket_title} - Ticket #{ticket_id}",
            "body": """Dear {recipient_name},

Thank you for your patience. We are actively investigating your request.

Our team is reviewing your account and information to determine the appropriate resolution. We will contact you as soon as we have more information.

Ticket ID: {ticket_id}

If you have any questions in the meantime, please reply to this email or contact us at {support_email}.

Best regards,
Support Team""",
        },
        EmailTemplate.RESOLUTION: {
            "subject": "Resolution: {ticket_title} - Ticket #{ticket_id}",
            "body": """Dear {recipient_name},

Good news! We have resolved your issue and your account access has been restored.

Please try accessing your account again at your earliest convenience. If you are able to successfully access everything, please reply to confirm that the issue is resolved.

If you continue to experience any difficulties, please let us know immediately so we can investigate further.

Ticket ID: {ticket_id}

Thank you for your patience.

Best regards,
Support Team
{support_email}""",
        },
        EmailTemplate.MANUAL_REVIEW: {
            "subject": "Update on Your Request - Ticket #{ticket_id}",
            "body": """Dear {recipient_name},

Thank you for your support request. Your case requires further investigation by our support team.

We are reviewing your account information and will determine the appropriate next steps. We will contact you as soon as we have completed our review.

Ticket ID: {ticket_id}
Issue: {ticket_title}

If you have any questions in the meantime, please contact us at {support_email}.

Best regards,
Support Team""",
        },
        EmailTemplate.FOLLOW_UP: {
            "subject": "Follow-up: {ticket_title} - Ticket #{ticket_id}",
            "body": """Dear {recipient_name},

We wanted to follow up on your support request (Ticket #{ticket_id}).

Are you now able to access your account successfully? Please let us know whether your issue has been resolved or if you are still experiencing difficulties.

If you are still experiencing issues, we are happy to assist further. Please reply to this email or contact us at {support_email}.

Best regards,
Support Team""",
        },
        EmailTemplate.SYSTEM_ERROR: {
            "subject": "Update on Your Support Request - Ticket #{ticket_id}",
            "body": """Dear {recipient_name},

Thank you for your support request. We are currently experiencing a processing delay and have not yet been able to investigate your request fully.

Our support team is aware of this issue and is working to resolve it. We will contact you as soon as we can proceed with investigating your request.

Ticket ID: {ticket_id}

We appreciate your patience. If you have urgent concerns, please contact us at {support_email}.

Best regards,
Support Team""",
        },
    }

    @staticmethod
    def render(context: EmailContext) -> tuple[str, str]:
        """Render email subject and body from context.

        Args:
            context: Email context with template and data

        Returns:
            Tuple of (subject, body)

        Raises:
            ValueError: If template not found
        """
        template = EmailTemplateRenderer.TEMPLATES.get(context.template)
        if not template:
            raise ValueError(f"Unknown email template: {context.template}")

        subject = template["subject"]
        body = template["body"]

        # Use safe fallback for empty recipient name
        recipient_name = context.recipient_name if context.recipient_name else "Hello"

        # Format with context
        format_dict = {
            "recipient_name": recipient_name,
            "recipient_email": context.recipient_email,
            "ticket_id": context.ticket_id,
            "ticket_title": context.ticket_title,
            "action_summary": context.action_summary or "",
            "next_steps": context.next_steps or "",
            "next_update_at": context.next_update_at or "",
            "support_email": context.support_email,
        }

        try:
            subject = subject.format(**format_dict)
            body = body.format(**format_dict)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

        return subject, body
