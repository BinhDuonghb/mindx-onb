"""Phase 4: Workflow Integration Tests - Verify email templates with acknowledgement."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.gmail import GmailService, EmailContext, EmailTemplate
from srcs.models import Ticket, Employee, EmployeeStatus
from srcs.services.ticket_analyzer import AnalysisResult, IssueType
from srcs.services.decision_service import Decision, DeactivationReason


class TestLoginWorkflowEmailIntegration:
    """Test email service integration with LoginWorkflow."""

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

    def test_successful_reactivation_sends_resolution_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send RESOLUTION email only on successful reactivation (not ACK).

        Phase 1 Communication Policy: Send exactly one email per cycle based on outcome.
        Successful reactivation → RESOLUTION only.
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

        # Execute
        result = workflow_with_email.execute(ticket_id=1)

        # Verify result
        assert result.success is True
        assert result.action_taken == "account_reactivated"

        # Verify EXACTLY ONE email sent (RESOLUTION only, not ACK)
        assert gmail_service.send_email.call_count == 1

        # Extract template
        email_context = gmail_service.send_email.call_args[0][0]

        # Verify it's RESOLUTION, not ACK
        assert email_context.template == EmailTemplate.RESOLUTION
        assert email_context.recipient_email == "john@company.com"
        assert email_context.ticket_id == 1

    def test_escalated_manual_review_sends_escalation_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send MANUAL_REVIEW email only when escalating (not ACK).

        Phase 1 Communication Policy: Send exactly one email per cycle based on outcome.
        Escalation → MANUAL_REVIEW only.
        """
        ticket = Ticket(
            id=2,
            name="Cannot login",
            email_from="jane@company.com",
        )

        employee = Employee(
            employee_id="EMP002",
            name="Jane Smith",
            email="jane@company.com",
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

        # Execute
        result = workflow_with_email.execute(ticket_id=2)

        # Verify escalation
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"

        # Verify EXACTLY ONE email sent (MANUAL_REVIEW only, not ACK)
        assert gmail_service.send_email.call_count == 1

        # Extract template
        email_context = gmail_service.send_email.call_args[0][0]

        # Verify it's MANUAL_REVIEW, not ACK
        assert email_context.template == EmailTemplate.MANUAL_REVIEW
        assert email_context.recipient_email == "jane@company.com"
        assert email_context.ticket_id == 2

    def test_non_login_issue_sends_no_email(self, workflow_with_email, gmail_service):
        """Should send no email for non-login issues (skipped).

        Phase 1 Communication Policy: Non-login issues are skipped without customer notification.
        """
        ticket = Ticket(
            id=3,
            name="General question",
            email_from="bob@company.com",
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,
            issue_type=None,
            reason="Not a login issue",
            confidence=0.85,
        )

        # Execute
        result = workflow_with_email.execute(ticket_id=3)

        # Verify skipped
        assert result.success is True
        assert result.action_taken == "skipped"

        # Verify NO emails sent (skipped = no communication)
        assert gmail_service.send_email.call_count == 0

    def test_employee_not_found_sends_escalation_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send MANUAL_REVIEW email when employee not found (not ACK).

        Phase 1 Communication Policy: Send exactly one email per cycle based on outcome.
        Employee not found → escalate → MANUAL_REVIEW only.
        """
        ticket = Ticket(
            id=4,
            name="Cannot login",
            email_from="unknown@company.com",
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = None
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )

        # Execute
        result = workflow_with_email.execute(ticket_id=4)

        # Verify escalation
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"

        # Verify EXACTLY ONE email sent (MANUAL_REVIEW only, not ACK)
        assert gmail_service.send_email.call_count == 1

        # Extract template
        email_context = gmail_service.send_email.call_args[0][0]

        # Verify it's MANUAL_REVIEW, not ACK
        assert email_context.template == EmailTemplate.MANUAL_REVIEW
        assert email_context.recipient_email == "unknown@company.com"
        assert email_context.ticket_id == 4

    def test_hr_reactivation_failure_sends_escalation_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send MANUAL_REVIEW email when HR reactivation fails (not ACK).

        Phase 1 Communication Policy: Send exactly one email per cycle based on outcome.
        Reactivation failure → escalate → MANUAL_REVIEW only.
        """
        ticket = Ticket(
            id=5,
            name="Cannot login",
            email_from="john@company.com",
        )

        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )
        workflow_with_email.hr_client.reactivate_lms_account.return_value = False

        # Execute
        result = workflow_with_email.execute(ticket_id=5)

        # Verify escalation (reactivation failed)
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"

        # Verify EXACTLY ONE email sent (MANUAL_REVIEW only, not ACK or RESOLUTION)
        assert gmail_service.send_email.call_count == 1

        # Extract template
        email_context = gmail_service.send_email.call_args[0][0]

        # Verify it's MANUAL_REVIEW, not RESOLUTION
        assert email_context.template == EmailTemplate.MANUAL_REVIEW
        assert email_context.recipient_email == "john@company.com"
        assert email_context.ticket_id == 5

    def test_email_send_failure_does_not_fail_workflow(self, workflow_with_email, gmail_service):
        """Should continue workflow even if email send fails.

        Email failures are non-fatal; workflow succeeds regardless.
        """
        ticket = Ticket(
            id=6,
            name="Cannot login",
            email_from="john@company.com",
        )

        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )
        workflow_with_email.hr_client.reactivate_lms_account.return_value = True

        # Mock email send to fail
        gmail_service.send_email.return_value = False

        # Execute
        result = workflow_with_email.execute(ticket_id=6)

        # Workflow should still succeed even though email failed
        assert result.success is True
        assert result.action_taken == "account_reactivated"

    def test_email_context_respects_hr_privacy(self, workflow_with_email, gmail_service):
        """Should NOT include HR data in customer emails per Week 4 requirements.

        Customer emails must be privacy-respecting: no sensitive HR information.
        """
        ticket = Ticket(
            id=7,
            name="Cannot login",
            email_from="alice@company.com",
        )

        employee = Employee(
            employee_id="EMP007",
            name="Alice Brown",
            email="alice@company.com",
            status=EmployeeStatus.ACTIVE,
            department="Engineering",
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow_with_email.ticket_client.get_ticket.return_value = ticket
        workflow_with_email.hr_client.get_employee_by_email.return_value = employee
        workflow_with_email.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )
        workflow_with_email.hr_client.reactivate_lms_account.return_value = True

        # Execute
        result = workflow_with_email.execute(ticket_id=7)

        # Verify success
        assert result.success is True

        # Verify exactly one email sent (RESOLUTION)
        assert gmail_service.send_email.call_count == 1

        # Check email context doesn't include HR data
        email_context = gmail_service.send_email.call_args[0][0]

        # Week 4: EmailContext should NOT have employee_id, department, deactivation_reason
        assert not hasattr(email_context, 'employee_id')
        assert not hasattr(email_context, 'department')
        assert not hasattr(email_context, 'deactivation_reason')

        # But it should have the public fields
        assert email_context.recipient_email == "alice@company.com"
        assert email_context.ticket_id == 7


class TestLoginWorkflowWithoutEmailService:
    """Test workflow works without email service (backwards compatibility)."""

    def test_workflow_executes_without_email_service(self):
        """Should execute successfully even if no email service provided."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="john@company.com",
        )

        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Create workflow WITHOUT email service
        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=None,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # Execute - should work fine
        result = workflow.execute(ticket_id=1)

        assert result.success is True
        assert result.action_taken == "account_reactivated"
