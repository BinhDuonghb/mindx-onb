"""Test outcome-first communication policy - RED phase.

Verify that exactly ONE email is sent per execution based on workflow outcome.
Never send ACK + Resolution in same execution (outcome-first policy).
"""

import pytest
from unittest.mock import Mock
from pathlib import Path

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.communication_state import CommunicationStateTracker
from srcs.services.gmail import EmailTemplate, CommunicationEvent
from srcs.services.decision_service import Decision
from srcs.repositories.automation_state_repository import AutomationStateRepository


class TestOutcomeCommunicationPolicy:
    """Test outcome-first communication policy."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    @pytest.fixture
    def state_repo(self, temp_db):
        """Create state repository."""
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def workflow(self, state_repo):
        """Create workflow with mocked clients and persistent state."""
        gmail_service = Mock()
        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
            state_repo=state_repo,
        )
        return workflow

    def test_successful_reactivation_sends_resolution_only(self, workflow):
        """Successful reactivation should send RESOLUTION email only."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP001",
            name="User One",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # Execute
        result = workflow.execute(ticket_id=1)

        # Verify exactly ONE email sent: RESOLUTION
        assert workflow.gmail_service.send_email.call_count == 1
        context = workflow.gmail_service.send_email.call_args[0][0]
        assert context.template == EmailTemplate.RESOLUTION

        # Verify NO ACK email was sent
        for call in workflow.gmail_service.send_email.call_args_list:
            assert call[0][0].template != EmailTemplate.ACKNOWLEDGEMENT

    def test_escalation_sends_manual_review_only(self, workflow):
        """Escalation should send MANUAL_REVIEW email only."""
        ticket = Ticket(
            id=2,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP002",
            name="User Two",
            email="user@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.EMPLOYEE_TERMINATED,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )

        # Execute
        result = workflow.execute(ticket_id=2)

        # Verify exactly ONE email sent: MANUAL_REVIEW
        assert workflow.gmail_service.send_email.call_count == 1
        context = workflow.gmail_service.send_email.call_args[0][0]
        assert context.template == EmailTemplate.MANUAL_REVIEW

        # Verify NO ACK email was sent
        for call in workflow.gmail_service.send_email.call_args_list:
            assert call[0][0].template != EmailTemplate.ACKNOWLEDGEMENT

    def test_skipped_sends_no_email(self, workflow):
        """Skipped tickets should send no email."""
        ticket = Ticket(
            id=3,
            name="General question",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP003",
            name="User Three",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,  # Not a login issue
            issue_type=None,
            reason="Not a login issue",
            confidence=0.85,
        )

        # Execute
        result = workflow.execute(ticket_id=3)

        # Verify NO email sent
        assert workflow.gmail_service.send_email.call_count == 0

    def test_failure_schedules_retry_sends_no_email(self, workflow):
        """Retry-scheduled failures should send no email (retry later)."""
        ticket = Ticket(
            id=4,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP004",
            name="User Four",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = False  # Failure

        # Execute
        result = workflow.execute(ticket_id=4)

        # Verify failure scheduled retry
        assert result.action_taken == "retry_scheduled"

        # Verify NO email sent (will be sent on retry success)
        assert workflow.gmail_service.send_email.call_count == 0

    def test_no_ack_and_resolution_together(self, workflow, state_repo):
        """Never send ACK and RESOLUTION in same execution."""
        ticket = Ticket(
            id=5,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP005",
            name="User Five",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # Execute - should send RESOLUTION (not ACK)
        result = workflow.execute(ticket_id=5)

        # Collect all sent emails
        sent_templates = []
        for call in workflow.gmail_service.send_email.call_args_list:
            sent_templates.append(call[0][0].template)

        # Verify ACK and RESOLUTION are never sent together
        has_ack = EmailTemplate.ACKNOWLEDGEMENT in sent_templates
        has_resolution = EmailTemplate.RESOLUTION in sent_templates
        assert not (has_ack and has_resolution), "Cannot send ACK and RESOLUTION together"

        # For successful reactivation, should have RESOLUTION
        assert EmailTemplate.RESOLUTION in sent_templates
        assert EmailTemplate.ACKNOWLEDGEMENT not in sent_templates

    def test_email_deduplication_across_executions(self, workflow, state_repo):
        """Email deduplication should prevent resending across executions."""
        ticket = Ticket(
            id=6,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP006",
            name="User Six",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # First execution - sends RESOLUTION
        result1 = workflow.execute(ticket_id=6)
        assert workflow.gmail_service.send_email.call_count == 1

        # Reset mock
        workflow.gmail_service.reset_mock()

        # Second execution (re-poll) - should NOT resend RESOLUTION
        result2 = workflow.execute(ticket_id=6)
        assert workflow.gmail_service.send_email.call_count == 0  # Deduplication worked
