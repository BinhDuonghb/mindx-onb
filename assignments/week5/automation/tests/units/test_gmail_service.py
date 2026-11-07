"""Unit tests for Gmail service - Phase 1 & 2: Templates and SMTP Transport."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from srcs.services.gmail import GmailService, EmailContext, EmailTemplate
from srcs.services.gmail.email_templates import EmailTemplateRenderer


# ==============================================================================
# Phase 1: Template and Configuration Tests
# ==============================================================================

class TestEmailTemplateRenderer:
    """Test email template rendering and content generation."""

    def test_render_account_reactivated_with_content(self):
        """Should render account reactivated template with proper content."""
        context = EmailContext(
            recipient_email="john@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot login",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
            employee_name="John Doe",
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Verify subject
        assert "Reactivated" in subject
        # Verify recipient name appears in body
        assert "John Doe" in body
        # Verify content-specific phrases
        assert "log in" in body.lower()

    def test_render_escalated_manual_review_with_ticket_details(self):
        """Should render escalated template with ticket details."""
        context = EmailContext(
            recipient_email="jane@company.com",
            recipient_name="Jane Smith",
            ticket_id=99,
            ticket_title="Account locked",
            template=EmailTemplate.ESCALATED_MANUAL_REVIEW,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "Review" in subject or "Manual" in subject
        assert "99" in body  # Ticket ID should appear
        assert "Account locked" in body  # Title should appear

    def test_render_employee_terminated_template(self):
        """Should render terminated employee template."""
        context = EmailContext(
            recipient_email="terminated@company.com",
            recipient_name="Terminated Employee",
            ticket_id=1,
            ticket_title="Login request",
            template=EmailTemplate.EMPLOYEE_TERMINATED,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert subject is not None
        assert body is not None
        assert "1" in body  # Ticket ID should appear

    def test_render_system_error_template(self):
        """Should render system error template."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=5,
            ticket_title="System Error Test",
            template=EmailTemplate.SYSTEM_ERROR,
            error_details="Database connection timeout",
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert subject is not None
        assert "5" in body

    def test_render_password_reset_template(self):
        """Should render password reset template."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=7,
            ticket_title="Password Reset",
            template=EmailTemplate.PASSWORD_RESET_INITIATED,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "Password" in subject or "password" in body.lower()
        assert "7" in body

    def test_render_with_custom_support_email(self):
        """Should use custom support email in template."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=1,
            ticket_title="Test",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
            support_email="help@example.com",
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "help@example.com" in body

    def test_render_with_default_support_email(self):
        """Should use default support email when not specified."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=1,
            ticket_title="Test",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "support@company.com" in body

    def test_render_with_unknown_template_raises_error(self):
        """Should raise ValueError for unknown template."""
        context = EmailContext(
            recipient_email="test@company.com",
            recipient_name="Test User",
            ticket_id=1,
            ticket_title="Test",
            template="unknown_template",  # type: ignore
        )

        with pytest.raises(ValueError, match="Unknown email template"):
            EmailTemplateRenderer.render(context)

    def test_render_all_templates_succeed(self):
        """Should successfully render all template types."""
        templates = [
            EmailTemplate.ACCOUNT_REACTIVATED,
            EmailTemplate.ESCALATED_MANUAL_REVIEW,
            EmailTemplate.EMPLOYEE_TERMINATED,
            EmailTemplate.SYSTEM_ERROR,
            EmailTemplate.PASSWORD_RESET_INITIATED,
        ]

        for template in templates:
            context = EmailContext(
                recipient_email="test@company.com",
                recipient_name="Test User",
                ticket_id=1,
                ticket_title="Test",
                template=template,
            )
            subject, body = EmailTemplateRenderer.render(context)
            assert subject
            assert body


class TestGmailServiceInitialization:
    """Test Gmail service initialization and configuration validation."""

    def test_initialize_with_all_credentials(self):
        """Should initialize with valid credentials."""
        service = GmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="test@gmail.com",
            smtp_password="password123",
            from_email="test@gmail.com",
        )

        assert service.smtp_host == "smtp.gmail.com"
        assert service.smtp_port == 587
        assert service.smtp_username == "test@gmail.com"
        assert service.smtp_password == "password123"
        assert service.from_email == "test@gmail.com"

    def test_initialize_missing_username_raises_error(self):
        """Should raise error if username missing."""
        with pytest.raises(ValueError, match="Missing required SMTP credentials"):
            GmailService(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_username="",
                smtp_password="password123",
                from_email="test@gmail.com",
            )

    def test_initialize_missing_password_raises_error(self):
        """Should raise error if password missing."""
        with pytest.raises(ValueError, match="Missing required SMTP credentials"):
            GmailService(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_username="test@gmail.com",
                smtp_password="",
                from_email="test@gmail.com",
            )

    def test_initialize_missing_from_email_raises_error(self):
        """Should raise error if from_email missing."""
        with pytest.raises(ValueError, match="Missing required SMTP credentials"):
            GmailService(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_username="test@gmail.com",
                smtp_password="password123",
                from_email="",
            )

    def test_initialize_none_username_raises_error(self):
        """Should raise error if username is None."""
        with pytest.raises(ValueError, match="Missing required SMTP credentials"):
            GmailService(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_username=None,  # type: ignore
                smtp_password="password123",
                from_email="test@gmail.com",
            )


class TestGmailServiceSendEmail:
    """Test email sending business logic."""

    @pytest.fixture
    def gmail_service(self):
        """Create Gmail service with test credentials."""
        return GmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="test@gmail.com",
            smtp_password="password123",
            from_email="test@gmail.com",
        )

    def test_send_email_success(self, gmail_service):
        """Should send email successfully."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            result = gmail_service.send_email(context)

        assert result is True
        mock_send.assert_called_once()

    def test_send_email_renders_correct_content(self, gmail_service):
        """Should render and send correct email content."""
        context = EmailContext(
            recipient_email="john@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot login",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            gmail_service.send_email(context)

        # Verify _send_smtp was called with rendered content
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        # Verify email parameters
        assert call_kwargs["to_email"] == "john@company.com"
        assert "Reactivated" in call_kwargs["subject"]
        assert "John Doe" in call_kwargs["body"]

    def test_send_email_retries_on_smtp_exception(self, gmail_service):
        """Should retry on temporary SMTP failures."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            # First attempt fails, second succeeds
            mock_send.side_effect = [
                smtplib.SMTPException("Temporary error"),
                None,  # Success
            ]

            result = gmail_service.send_email(context, max_retries=3)

        assert result is True
        assert mock_send.call_count == 2

    def test_send_email_no_retry_on_auth_error(self, gmail_service):
        """Should NOT retry on authentication error."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            mock_send.side_effect = smtplib.SMTPAuthenticationError(
                535, "Invalid credentials"
            )

            result = gmail_service.send_email(context, max_retries=3)

        assert result is False
        # Auth error should not retry
        mock_send.assert_called_once()

    def test_send_email_fails_after_max_retries(self, gmail_service):
        """Should fail after max retries exceeded."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            mock_send.side_effect = smtplib.SMTPException("Persistent error")

            result = gmail_service.send_email(context, max_retries=2)

        assert result is False
        assert mock_send.call_count == 2

    def test_send_email_handles_invalid_context(self, gmail_service):
        """Should handle invalid context gracefully."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template="invalid",  # type: ignore
        )

        result = gmail_service.send_email(context)

        assert result is False


# ==============================================================================
# Phase 2: SMTP Transport Tests (mocking socket-level SMTP)
# ==============================================================================

class TestSMTPTransport:
    """Test SMTP transport layer behavior with mocked socket."""

    @pytest.fixture
    def gmail_service(self):
        """Create Gmail service with test credentials."""
        return GmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="test@gmail.com",
            smtp_password="password123",
            from_email="test@gmail.com",
        )

    @patch("smtplib.SMTP")
    def test_smtp_connection_parameters(self, mock_smtp, gmail_service):
        """Should connect with correct SMTP host and port."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test",
            body="Test body",
        )

        # Verify SMTP was initialized with correct parameters
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=30)

    @patch("smtplib.SMTP")
    def test_smtp_starttls_initiated(self, mock_smtp, gmail_service):
        """Should initiate STARTTLS for encryption."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test",
            body="Test body",
        )

        # Verify STARTTLS was called to upgrade connection
        mock_server.starttls.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_login_with_credentials(self, mock_smtp, gmail_service):
        """Should login with configured credentials."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test",
            body="Test body",
        )

        # Verify login called with username and password
        mock_server.login.assert_called_once_with("test@gmail.com", "password123")

    @patch("smtplib.SMTP")
    def test_smtp_send_message_called(self, mock_smtp, gmail_service):
        """Should call send_message with the MIME message."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test Subject",
            body="Test body content",
        )

        # Verify send_message was called once
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_message_structure(self, mock_smtp, gmail_service):
        """Should send properly structured MIME message."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test Subject",
            body="Test body content",
        )

        # Extract the message that was sent
        msg = mock_server.send_message.call_args[0][0]

        # Verify message headers
        assert msg["Subject"] == "Test Subject"
        assert msg["From"] == "test@gmail.com"
        assert msg["To"] == "user@company.com"

        # Verify message is multipart with text part
        payload = msg.get_payload()
        assert isinstance(payload, list)
        assert len(payload) > 0

        # First part should be text/plain
        body_part = payload[0]
        assert body_part.get_content_type() == "text/plain"

    @patch("smtplib.SMTP")
    def test_smtp_message_is_multipart(self, mock_smtp, gmail_service):
        """Should create multipart message for text content."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test",
            body="Test body",
        )

        msg = mock_server.send_message.call_args[0][0]

        # Verify it's a multipart message
        assert msg.is_multipart()

    @patch("smtplib.SMTP")
    def test_smtp_connection_error_raises(self, mock_smtp, gmail_service):
        """Should raise on connection error."""
        mock_smtp.return_value.__enter__.side_effect = ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            gmail_service._send_smtp(
                to_email="user@company.com",
                subject="Test",
                body="Test body",
            )

    @patch("smtplib.SMTP")
    def test_smtp_login_error_raises(self, mock_smtp, gmail_service):
        """Should raise on login error."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, "Invalid credentials"
        )

        with pytest.raises(smtplib.SMTPAuthenticationError):
            gmail_service._send_smtp(
                to_email="user@company.com",
                subject="Test",
                body="Test body",
            )


class TestSMTPConnectionValidation:
    """Test SMTP connection validation."""

    @pytest.fixture
    def gmail_service(self):
        """Create Gmail service with test credentials."""
        return GmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="test@gmail.com",
            smtp_password="password123",
            from_email="test@gmail.com",
        )

    @patch("smtplib.SMTP")
    def test_validate_connection_success(self, mock_smtp, gmail_service):
        """Should validate successful SMTP connection."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = gmail_service.validate_connection()

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@gmail.com", "password123")

    @patch("smtplib.SMTP")
    def test_validate_connection_auth_failure(self, mock_smtp, gmail_service):
        """Should handle authentication failure."""
        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPAuthenticationError(
            535, "Invalid credentials"
        )

        result = gmail_service.validate_connection()

        assert result is False

    @patch("smtplib.SMTP")
    def test_validate_connection_smtp_failure(self, mock_smtp, gmail_service):
        """Should handle SMTP connection failure."""
        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPException(
            "Connection failed"
        )

        result = gmail_service.validate_connection()

        assert result is False

    @patch("smtplib.SMTP")
    def test_validate_connection_network_error(self, mock_smtp, gmail_service):
        """Should handle network errors."""
        mock_smtp.return_value.__enter__.side_effect = ConnectionError("Network error")

        result = gmail_service.validate_connection()

        assert result is False


class TestEmailContext:
    """Test email context dataclass."""

    def test_create_minimal_context(self):
        """Should create context with required fields only."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        assert context.recipient_email == "user@company.com"
        assert context.recipient_name == "User Name"
        assert context.ticket_id == 1
        assert context.ticket_title == "Test Ticket"
        assert context.template == EmailTemplate.ACCOUNT_REACTIVATED

    def test_create_full_context(self):
        """Should create context with all fields populated."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
            employee_name="Employee Name",
            employee_id="EMP001",
            department="Sales",
            deactivation_reason="inactivity_30_days",
            action_taken="account_reactivated",
            support_email="support@example.com",
        )

        assert context.employee_name == "Employee Name"
        assert context.employee_id == "EMP001"
        assert context.department == "Sales"
        assert context.deactivation_reason == "inactivity_30_days"
        assert context.action_taken == "account_reactivated"
        assert context.support_email == "support@example.com"

    def test_context_optional_fields_default_to_none(self):
        """Should default optional fields to None."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        assert context.employee_name is None
        assert context.employee_id is None
        assert context.department is None
        assert context.deactivation_reason is None
        assert context.action_taken is None
        assert context.message is None
        assert context.error_details is None

    def test_context_support_email_defaults(self):
        """Should default support_email to company support."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.ACCOUNT_REACTIVATED,
        )

        assert context.support_email == "support@company.com"
