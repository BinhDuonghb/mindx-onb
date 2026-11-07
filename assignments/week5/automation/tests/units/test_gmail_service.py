"""Unit tests for Gmail service - Updated for Week 4 email templates."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from srcs.services.gmail import GmailService, EmailContext, EmailTemplate
from srcs.services.gmail.email_templates import EmailTemplateRenderer


# ==============================================================================
# Phase 1: Template Rendering Tests (Updated for Week 4)
# ==============================================================================

class TestEmailTemplateRenderer:
    """Test email template rendering and content generation."""

    def test_render_resolution_template(self):
        """Should render resolution template for successful reactivation."""
        context = EmailContext(
            recipient_email="john@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot login",
            template=EmailTemplate.RESOLUTION,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "Reactivated" in subject
        assert "John Doe" in body
        assert "logging in" in body.lower() or "try" in body.lower()

    def test_render_manual_review_template(self):
        """Should render manual review template with ticket details."""
        context = EmailContext(
            recipient_email="jane@company.com",
            recipient_name="Jane Smith",
            ticket_id=99,
            ticket_title="Account locked",
            template=EmailTemplate.MANUAL_REVIEW,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "Review" in subject or "Update" in subject
        assert "99" in body
        assert "Account locked" in body

    def test_render_acknowledgement_template(self):
        """Should render acknowledgement template."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=1,
            ticket_title="Login request",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert subject is not None
        assert body is not None
        assert "1" in body

    def test_render_system_error_template(self):
        """Should render system error template without raw exceptions."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=5,
            ticket_title="System Error Test",
            template=EmailTemplate.SYSTEM_ERROR,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert subject is not None
        assert "5" in body
        # Should not contain raw exception details
        assert "Traceback" not in body

    def test_render_follow_up_template(self):
        """Should render follow-up template."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=7,
            ticket_title="Follow-up Test",
            template=EmailTemplate.FOLLOW_UP,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "Follow" in subject or "follow" in body.lower()
        assert "7" in body

    def test_render_with_custom_support_email(self):
        """Should use custom support email in template."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User",
            ticket_id=1,
            ticket_title="Test",
            template=EmailTemplate.RESOLUTION,
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
            template=EmailTemplate.RESOLUTION,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "support@company.com" in body

    def test_render_all_templates_succeed(self):
        """All templates should render without error."""
        templates = [
            EmailTemplate.ACKNOWLEDGEMENT,
            EmailTemplate.INVESTIGATION_UPDATE,
            EmailTemplate.RESOLUTION,
            EmailTemplate.MANUAL_REVIEW,
            EmailTemplate.FOLLOW_UP,
            EmailTemplate.SYSTEM_ERROR,
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
            template=EmailTemplate.RESOLUTION,
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
            template=EmailTemplate.RESOLUTION,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            gmail_service.send_email(context)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

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
            template=EmailTemplate.RESOLUTION,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            mock_send.side_effect = [
                smtplib.SMTPException("Temporary error"),
                None,
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
            template=EmailTemplate.RESOLUTION,
        )

        with patch.object(gmail_service, "_send_smtp") as mock_send:
            mock_send.side_effect = smtplib.SMTPAuthenticationError(
                535, "Invalid credentials"
            )

            result = gmail_service.send_email(context, max_retries=3)

        assert result is False
        mock_send.assert_called_once()

    def test_send_email_fails_after_max_retries(self, gmail_service):
        """Should fail after max retries exceeded."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.RESOLUTION,
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
# Phase 2: SMTP Transport Tests
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

        mock_server.login.assert_called_once_with("test@gmail.com", "password123")

    @patch("smtplib.SMTP")
    def test_smtp_send_message_called(self, mock_smtp, gmail_service):
        """Should call send_message with the MIME message."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        gmail_service._send_smtp(
            to_email="user@company.com",
            subject="Test",
            body="Test body",
        )

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

        msg = mock_server.send_message.call_args[0][0]

        assert msg["Subject"] == "Test Subject"
        assert msg["From"] == "test@gmail.com"
        assert msg["To"] == "user@company.com"

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
            template=EmailTemplate.RESOLUTION,
        )

        assert context.recipient_email == "user@company.com"
        assert context.recipient_name == "User Name"
        assert context.ticket_id == 1
        assert context.ticket_title == "Test Ticket"
        assert context.template == EmailTemplate.RESOLUTION

    def test_create_full_context(self):
        """Should create context with all fields populated."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.RESOLUTION,
            action_summary="Account reactivated",
            next_steps="Please try logging in",
            support_email="support@example.com",
        )

        assert context.action_summary == "Account reactivated"
        assert context.next_steps == "Please try logging in"
        assert context.support_email == "support@example.com"

    def test_context_optional_fields_default_to_none(self):
        """Should default optional fields to None."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.RESOLUTION,
        )

        assert context.action_summary is None
        assert context.next_steps is None
        assert context.next_update_at is None

    def test_context_support_email_defaults(self):
        """Should default support_email to company support."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="User Name",
            ticket_id=1,
            ticket_title="Test Ticket",
            template=EmailTemplate.RESOLUTION,
        )

        assert context.support_email == "support@company.com"
