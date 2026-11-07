"""Phase 1 TDD: Email template tests following Week 4 communication structure.

RED phase - Write failing tests first to define requirements.
"""

import pytest
from srcs.services.gmail.email_templates import EmailTemplate, EmailContext, EmailTemplateRenderer


class TestEmailTemplateEnum:
    """Test the new EmailTemplate enum structure."""

    def test_acknowledgement_template_exists(self):
        """Should have ACKNOWLEDGEMENT template for initial contact."""
        assert hasattr(EmailTemplate, "ACKNOWLEDGEMENT")
        assert EmailTemplate.ACKNOWLEDGEMENT.value == "acknowledgement"

    def test_investigation_update_template_exists(self):
        """Should have INVESTIGATION_UPDATE for progress updates."""
        assert hasattr(EmailTemplate, "INVESTIGATION_UPDATE")
        assert EmailTemplate.INVESTIGATION_UPDATE.value == "investigation_update"

    def test_resolution_template_exists(self):
        """Should have RESOLUTION for successful reactivation."""
        assert hasattr(EmailTemplate, "RESOLUTION")
        assert EmailTemplate.RESOLUTION.value == "resolution"

    def test_manual_review_template_exists(self):
        """Should have MANUAL_REVIEW for ineligible cases."""
        assert hasattr(EmailTemplate, "MANUAL_REVIEW")
        assert EmailTemplate.MANUAL_REVIEW.value == "manual_review"

    def test_follow_up_template_exists(self):
        """Should have FOLLOW_UP for confirmation reminders."""
        assert hasattr(EmailTemplate, "FOLLOW_UP")
        assert EmailTemplate.FOLLOW_UP.value == "follow_up"

    def test_system_error_template_exists(self):
        """Should have SYSTEM_ERROR for failures."""
        assert hasattr(EmailTemplate, "SYSTEM_ERROR")
        assert EmailTemplate.SYSTEM_ERROR.value == "system_error"


class TestAcknowledgementTemplate:
    """Test ACKNOWLEDGEMENT email follows Week 4 structure."""

    def test_acknowledgement_includes_ticket_reference(self):
        """ACK should include ticket ID in subject and body."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Ticket reference in subject
        assert "42" in subject
        # Ticket reference in body
        assert "42" in body

    def test_acknowledgement_confirms_receipt(self):
        """ACK should confirm that the issue was received."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should acknowledge receipt
        assert "received" in body.lower() or "confirm" in body.lower()

    def test_acknowledgement_includes_next_steps(self):
        """ACK should explain what happens next."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should explain next steps
        assert "next" in body.lower() or "check" in body.lower() or "investigate" in body.lower()

    def test_acknowledgement_includes_support_contact(self):
        """ACK should include support contact."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.ACKNOWLEDGEMENT,
            support_email="support@example.com",
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "support@example.com" in body


class TestResolutionTemplate:
    """Test RESOLUTION email requests customer confirmation."""

    def test_resolution_explains_reactivation(self):
        """Resolution should explain that account was reactivated."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.RESOLUTION,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should explain reactivation
        assert "reactivat" in body.lower() or "access" in body.lower()

    def test_resolution_asks_for_confirmation(self):
        """Resolution should ask user to try login and confirm it works."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.RESOLUTION,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should ask user to try logging in
        assert "try" in body.lower() or "login" in body.lower() or "confirm" in body.lower()

    def test_resolution_does_not_claim_user_logged_in(self):
        """Resolution must NOT say 'you have successfully logged in'."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.RESOLUTION,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should NOT presume success
        assert "you have successfully logged in" not in body.lower()
        assert "you can now access" not in body.lower()

    def test_resolution_includes_ticket_id(self):
        """Resolution should reference the ticket ID."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.RESOLUTION,
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "42" in subject or "42" in body


class TestManualReviewTemplate:
    """Test MANUAL_REVIEW email protects HR privacy."""

    def test_manual_review_does_not_reveal_termination(self):
        """Manual review must NOT reveal employee termination status."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.MANUAL_REVIEW,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Must NOT reveal HR status
        assert "terminated" not in body.lower()
        assert "employment" not in body.lower()
        assert "fired" not in body.lower()

    def test_manual_review_indicates_under_review(self):
        """Manual review should indicate the request is under review."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.MANUAL_REVIEW,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should indicate ongoing review
        assert "review" in body.lower() or "investigating" in body.lower() or "looking" in body.lower()

    def test_manual_review_includes_support_contact(self):
        """Manual review should provide support contact."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.MANUAL_REVIEW,
            support_email="support@example.com",
        )

        subject, body = EmailTemplateRenderer.render(context)

        assert "support@example.com" in body


class TestFollowUpTemplate:
    """Test FOLLOW_UP email requests customer feedback."""

    def test_follow_up_references_completed_action(self):
        """Follow-up should reference the earlier reactivation."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.FOLLOW_UP,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should reference earlier action
        assert "follow" in subject.lower() or "follow" in body.lower()

    def test_follow_up_asks_for_customer_feedback(self):
        """Follow-up should ask if login now works."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.FOLLOW_UP,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should ask for feedback
        assert "can you" in body.lower() or "please let" in body.lower() or "confirm" in body.lower()

    def test_follow_up_offers_further_support(self):
        """Follow-up should offer additional help if still failing."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.FOLLOW_UP,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should offer help
        assert "help" in body.lower() or "assist" in body.lower() or "support" in body.lower()


class TestSystemErrorTemplate:
    """Test SYSTEM_ERROR email hides technical details."""

    def test_system_error_does_not_include_raw_exceptions(self):
        """System error must NOT include raw exception details."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.SYSTEM_ERROR,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Must NOT include raw exception details
        assert "AttributeError" not in body
        assert "NoneType" not in body
        assert "Traceback" not in body
        assert "exception" not in body.lower() or "processing" in body.lower()

    def test_system_error_indicates_delay(self):
        """System error should explain that processing was delayed."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.SYSTEM_ERROR,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should indicate delay/issue
        assert "delay" in body.lower() or "error" in body.lower() or "unable" in body.lower()

    def test_system_error_indicates_team_notification(self):
        """System error should indicate support team is aware."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Cannot access LMS",
            template=EmailTemplate.SYSTEM_ERROR,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should indicate team is aware
        assert "team" in body.lower() or "aware" in body.lower() or "notif" in body.lower()


class TestEmailContextSimplification:
    """Test that EmailContext is simplified per Week 4 requirements."""

    def test_context_has_public_fields_only(self):
        """EmailContext should have minimal public fields."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Test",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        # Public fields required
        assert context.recipient_email == "user@company.com"
        assert context.recipient_name == "John Doe"
        assert context.ticket_id == 42
        assert context.ticket_title == "Test"
        assert context.template == EmailTemplate.ACKNOWLEDGEMENT

    def test_context_has_support_email_default(self):
        """EmailContext should default support_email."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Test",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        assert context.support_email == "support@company.com"

    def test_context_safe_fallback_for_empty_name(self):
        """Empty recipient name should have safe fallback."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="",  # Empty name
            ticket_id=42,
            ticket_title="Test",
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        subject, body = EmailTemplateRenderer.render(context)

        # Should render safely (e.g., "Hello," instead of "Hello ,")
        assert "Hello" in body or "Thank you" in body
        assert ",," not in body  # No double commas


class TestTemplateRendering:
    """Test template rendering robustness."""

    def test_unknown_template_raises_error(self):
        """Unknown template should raise ValueError."""
        context = EmailContext(
            recipient_email="user@company.com",
            recipient_name="John Doe",
            ticket_id=42,
            ticket_title="Test",
            template="unknown_template",  # type: ignore
        )

        with pytest.raises(ValueError, match="Unknown email template"):
            EmailTemplateRenderer.render(context)

    def test_all_templates_render_successfully(self):
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
                recipient_email="user@company.com",
                recipient_name="John Doe",
                ticket_id=42,
                ticket_title="Test",
                template=template,
            )

            subject, body = EmailTemplateRenderer.render(context)

            assert subject, f"Template {template} produced empty subject"
            assert body, f"Template {template} produced empty body"
            assert "42" in subject or "42" in body, f"Template {template} missing ticket ID"
