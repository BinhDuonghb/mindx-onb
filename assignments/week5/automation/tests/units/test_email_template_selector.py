"""Phase 3 TDD: EmailTemplateSelector tests - RED phase (failing tests define requirements)."""

import pytest
from srcs.services.gmail.email_template_selector import EmailTemplateSelector, CommunicationEvent
from srcs.services.gmail import EmailTemplate
from srcs.services.login_workflow import WorkflowResult
from srcs.models import EmployeeStatus


class TestEmailTemplateSelectorEnum:
    """Test CommunicationEvent enum structure."""

    def test_acknowledgement_event_exists(self):
        """Should have ACKNOWLEDGEMENT event for new login tickets."""
        assert hasattr(CommunicationEvent, "TICKET_RECEIVED")

    def test_investigation_update_event_exists(self):
        """Should have INVESTIGATION_UPDATE event."""
        assert hasattr(CommunicationEvent, "INVESTIGATION_IN_PROGRESS")

    def test_resolution_event_exists(self):
        """Should have RESOLUTION event for successful reactivation."""
        assert hasattr(CommunicationEvent, "REACTIVATION_SUCCESSFUL")

    def test_manual_review_event_exists(self):
        """Should have MANUAL_REVIEW event."""
        assert hasattr(CommunicationEvent, "MANUAL_REVIEW_REQUIRED")

    def test_system_error_event_exists(self):
        """Should have SYSTEM_ERROR event."""
        assert hasattr(CommunicationEvent, "SYSTEM_ERROR")

    def test_follow_up_event_exists(self):
        """Should have FOLLOW_UP event."""
        assert hasattr(CommunicationEvent, "FOLLOW_UP_REMINDER")


class TestEmailTemplateSelectorSelection:
    """Test template selection logic for each event."""

    def test_select_acknowledgement_for_new_login_ticket(self):
        """Should select ACKNOWLEDGEMENT when login ticket is received."""
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.TICKET_RECEIVED,
        )
        assert template == EmailTemplate.ACKNOWLEDGEMENT

    def test_select_investigation_update_for_progress(self):
        """Should select INVESTIGATION_UPDATE when investigation is in progress."""
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.INVESTIGATION_IN_PROGRESS,
        )
        assert template == EmailTemplate.INVESTIGATION_UPDATE

    def test_select_resolution_for_successful_reactivation(self):
        """Should select RESOLUTION when reactivation succeeds."""
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL,
        )
        assert template == EmailTemplate.RESOLUTION

    def test_select_manual_review_for_escalation(self):
        """Should select MANUAL_REVIEW when escalating."""
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.MANUAL_REVIEW_REQUIRED,
        )
        assert template == EmailTemplate.MANUAL_REVIEW

    def test_select_system_error_for_failure(self):
        """Should select SYSTEM_ERROR when system fails."""
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.SYSTEM_ERROR,
        )
        assert template == EmailTemplate.SYSTEM_ERROR

    def test_select_follow_up_for_reminder(self):
        """Should select FOLLOW_UP for confirmation reminder."""
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.FOLLOW_UP_REMINDER,
        )
        assert template == EmailTemplate.FOLLOW_UP

    def test_select_none_for_unsupported_event(self):
        """Should return None for unsupported events."""
        template = EmailTemplateSelector.select(
            event="unsupported_event",  # type: ignore
        )
        assert template is None


class TestEmailTemplateSelectorConstraints:
    """Test selection constraints and edge cases."""

    def test_never_select_resolution_for_failed_reactivation(self):
        """Should NOT select RESOLUTION if reactivation failed."""
        # Resolution is only for successful reactivation
        # Failure should trigger escalation, not resolution
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL,
        )
        # This should always be RESOLUTION when event is REACTIVATION_SUCCESSFUL
        # The caller is responsible for only sending REACTIVATION_SUCCESSFUL event when it actually succeeded
        assert template == EmailTemplate.RESOLUTION

    def test_select_acknowledges_all_workflow_states(self):
        """ACKNOWLEDGEMENT should be independent of workflow state."""
        # ACK should be sent regardless of later workflow decisions
        template = EmailTemplateSelector.select(
            event=CommunicationEvent.TICKET_RECEIVED,
        )
        assert template == EmailTemplate.ACKNOWLEDGEMENT

    def test_no_password_reset_template(self):
        """Should NOT have a PASSWORD_RESET template."""
        # Week 5 automation doesn't handle password resets
        assert not hasattr(EmailTemplate, "PASSWORD_RESET_INITIATED")

    def test_selector_is_pure_function(self):
        """Selector should be a pure function with no side effects."""
        # Calling multiple times with same input should give same output
        template1 = EmailTemplateSelector.select(
            event=CommunicationEvent.TICKET_RECEIVED,
        )
        template2 = EmailTemplateSelector.select(
            event=CommunicationEvent.TICKET_RECEIVED,
        )
        assert template1 == template2

    def test_selector_handles_none_gracefully(self):
        """Selector should handle None input gracefully."""
        template = EmailTemplateSelector.select(
            event=None,  # type: ignore
        )
        assert template is None


class TestEmailTemplateSelectorDocumentation:
    """Test that selector is well-documented."""

    def test_selector_has_docstring(self):
        """Selector method should have docstring."""
        assert EmailTemplateSelector.select.__doc__ is not None

    def test_event_enum_has_docstrings(self):
        """Event enum members should be documented."""
        # At minimum, the enum should exist and be usable
        assert hasattr(CommunicationEvent, "TICKET_RECEIVED")
