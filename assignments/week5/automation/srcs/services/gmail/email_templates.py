"""Email templates and rendering context for automation responses."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EmailTemplate(str, Enum):
    """Email template types."""

    ACCOUNT_REACTIVATED = "account_reactivated"
    ESCALATED_MANUAL_REVIEW = "escalated_manual_review"
    EMPLOYEE_TERMINATED = "employee_terminated"
    SYSTEM_ERROR = "system_error"
    PASSWORD_RESET_INITIATED = "password_reset_initiated"


@dataclass
class EmailContext:
    """Context data for email template rendering."""

    recipient_email: str
    recipient_name: str
    ticket_id: int
    ticket_title: str
    template: EmailTemplate

    # Template-specific fields
    employee_name: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    deactivation_reason: Optional[str] = None
    action_taken: Optional[str] = None
    message: Optional[str] = None
    error_details: Optional[str] = None
    support_email: str = "support@company.com"


class EmailTemplateRenderer:
    """Renders email content from templates and context."""

    TEMPLATES = {
        EmailTemplate.ACCOUNT_REACTIVATED: {
            "subject": "Your Account Has Been Reactivated",
            "body": """Dear {recipient_name},

Your account has been successfully reactivated. You should now be able to log in.

If you continue to experience any issues, please reply to this email or contact our support team at {support_email}.

Best regards,
Automation Support Team""",
        },
        EmailTemplate.ESCALATED_MANUAL_REVIEW: {
            "subject": "Your Login Request - Manual Review",
            "body": """Dear {recipient_name},

Thank you for reaching out. Your login issue has been received and is being reviewed by our support team.

We will investigate your issue and get back to you shortly.

Ticket ID: {ticket_id}
Title: {ticket_title}

If you have any additional information, please reply to this email.

Best regards,
Support Team""",
        },
        EmailTemplate.EMPLOYEE_TERMINATED: {
            "subject": "Account Access Request",
            "body": """Dear {recipient_name},

Thank you for contacting us. We are unable to process your login request at this time.

Our support team will contact you regarding your account status.

Ticket ID: {ticket_id}

Please contact our support team at {support_email} if you have any questions.

Best regards,
Support Team""",
        },
        EmailTemplate.SYSTEM_ERROR: {
            "subject": "We're Looking Into Your Issue",
            "body": """Dear {recipient_name},

Thank you for reporting your issue. An unexpected error occurred while processing your request, but our team has been notified.

We will investigate and get back to you shortly.

Ticket ID: {ticket_id}
Title: {ticket_title}

Contact us at {support_email} if you have urgent concerns.

Best regards,
Support Team""",
        },
        EmailTemplate.PASSWORD_RESET_INITIATED: {
            "subject": "Password Reset Initiated",
            "body": """Dear {recipient_name},

A password reset has been initiated for your account.

Please check your email for further instructions.

Ticket ID: {ticket_id}

If you did not request this, please contact us at {support_email}.

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

        # Format with context
        format_dict = {
            "recipient_name": context.recipient_name,
            "recipient_email": context.recipient_email,
            "ticket_id": context.ticket_id,
            "ticket_title": context.ticket_title,
            "employee_name": context.employee_name or "",
            "employee_id": context.employee_id or "",
            "department": context.department or "",
            "deactivation_reason": context.deactivation_reason or "",
            "action_taken": context.action_taken or "",
            "message": context.message or "",
            "error_details": context.error_details or "",
            "support_email": context.support_email,
        }

        try:
            subject = subject.format(**format_dict)
            body = body.format(**format_dict)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

        return subject, body
