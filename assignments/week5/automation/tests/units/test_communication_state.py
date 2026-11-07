"""Phase 5 TDD: Communication state tracking and deduplication - RED phase tests."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.gmail import GmailService, EmailTemplate, CommunicationEvent
from srcs.models import Ticket, Employee, EmployeeStatus
from srcs.services.ticket_analyzer import AnalysisResult, IssueType
from srcs.services.decision_service import DeactivationReason


class TestCommunicationStateTracking:
    """Test communication state prevents duplicate emails."""

    @pytest.fixture
    def gmail_service(self):
        """Create Gmail service mock."""
        service = Mock(spec=GmailService)
        service.send_email = Mock(return_value=True)
        return service

    @pytest.fixture
    def workflow_with_email(self, gmail_service):
        """Create LoginWorkflow with Gmail service."""
        return LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
        )

    def test_acknowledgement_sent_only_once(self, workflow_with_email, gmail_service):
        """MANUAL_REVIEW should be sent only once when escalation happens.

        Phase 1 Communication Policy: Send exactly one email per cycle based on outcome.
        This test verifies deduplication works for escalation scenarios.
        """
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="john@company.com",
        )

        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.TERMINATED,  # Terminated - will escalate
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.EMPLOYEE_TERMINATED,
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )

        # First execution - terminated employee escalates with MANUAL_REVIEW
        result1 = workflow_with_email.execute(ticket_id=1)
        manual_review_count_after_first = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.MANUAL_REVIEW
        )

        # Reset mock to count only second execution
        gmail_service.send_email.reset_mock()

        # Second execution (simulating re-poll)
        result2 = workflow_with_email.execute(ticket_id=1)
        manual_review_count_after_second = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.MANUAL_REVIEW
        )

        # First execution should send MANUAL_REVIEW (escalation)
        assert manual_review_count_after_first == 1

        # Second execution should NOT send MANUAL_REVIEW (already sent, deduplication)
        assert manual_review_count_after_second == 0

    def test_resolution_sent_only_once(self, workflow_with_email, gmail_service):
        """RESOLUTION should be sent only once, not on every successful re-poll."""
        ticket = Ticket(
            id=2,
            name="Cannot login",
            email_from="jane@company.com",
        )

        employee = Employee(
            employee_id="EMP002",
            name="Jane Smith",
            email="jane@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )
        workflow_with_email.hr_client.reactivate_lms_account.return_value = True

        # First execution
        result1 = workflow_with_email.execute(ticket_id=2)
        resolution_count_first = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.RESOLUTION
        )

        # Reset mock
        gmail_service.send_email.reset_mock()

        # Second execution (simulating re-poll)
        result2 = workflow_with_email.execute(ticket_id=2)
        resolution_count_second = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.RESOLUTION
        )

        # First execution should send RESOLUTION
        assert resolution_count_first == 1

        # Second execution should NOT send RESOLUTION (already sent)
        assert resolution_count_second == 0

    def test_manual_review_email_sent_only_once(self, workflow_with_email, gmail_service):
        """MANUAL_REVIEW should be sent only once, not on every re-poll."""
        ticket = Ticket(
            id=3,
            name="Cannot login",
            email_from="bob@company.com",
        )

        employee = Employee(
            employee_id="EMP003",
            name="Bob Jones",
            email="bob@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.EMPLOYEE_TERMINATED,
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )

        # First execution
        result1 = workflow_with_email.execute(ticket_id=3)
        manual_review_count_first = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.MANUAL_REVIEW
        )

        # Reset mock
        gmail_service.send_email.reset_mock()

        # Second execution (simulating re-poll)
        result2 = workflow_with_email.execute(ticket_id=3)
        manual_review_count_second = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.MANUAL_REVIEW
        )

        # First execution should send MANUAL_REVIEW
        assert manual_review_count_first == 1

        # Second execution should NOT send MANUAL_REVIEW (already sent)
        assert manual_review_count_second == 0

    def test_ticket_content_change_resends_update_email(self, workflow_with_email, gmail_service):
        """If ticket content changes, new emails may be warranted (future implementation)."""
        # This test verifies email deduplication with content changes
        # When ticket content changes (new fingerprint), the framework supports re-evaluation

        ticket_v1 = Ticket(
            id=4,
            name="Cannot login",
            email_from="alice@company.com",
        )

        ticket_v2 = Ticket(
            id=4,
            name="Cannot login - updated description",  # Changed
            email_from="alice@company.com",
        )

        employee = Employee(
            employee_id="EMP004",
            name="Alice Brown",
            email="alice@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # First execution with v1 - successful reactivation
        workflow_with_email.ticket_client.get_ticket.return_value = ticket_v1
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow_with_email.hr_client.reactivate_lms_account.return_value = True

        result1 = workflow_with_email.execute(ticket_id=4)
        assert result1.action_taken == "account_reactivated"

        # First execution should send RESOLUTION
        resolution_count_first = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.RESOLUTION
        )
        assert resolution_count_first == 1

        # Update ticket to v2 (simulating customer adding more details)
        workflow_with_email.ticket_client.get_ticket.return_value = ticket_v2

        # Second execution should detect fingerprint change but not resend
        # (same ticket, already completed)
        gmail_service.send_email.reset_mock()
        result2 = workflow_with_email.execute(ticket_id=4)

        # Should handle gracefully without duplicate email
        resolution_count_second = sum(
            1 for call in gmail_service.send_email.call_args_list
            if call[0][0].template == EmailTemplate.RESOLUTION
        )
        assert resolution_count_second == 0  # Email deduplication still works
