"""Phase 3: Workflow Integration Tests - Verify email templates in LoginWorkflow."""

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

    def test_successful_reactivation_sends_account_reactivated_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send account reactivated email on successful reactivation."""
        # Setup
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

        # Verify email sent with correct template
        assert result.success is True
        assert result.action_taken == "account_reactivated"

        # Verify email was sent
        gmail_service.send_email.assert_called_once()
        call_args = gmail_service.send_email.call_args[0][0]

        # Verify email context
        assert isinstance(call_args, EmailContext)
        assert call_args.recipient_email == "john@company.com"
        assert call_args.recipient_name == "John Doe"
        assert call_args.template == EmailTemplate.ACCOUNT_REACTIVATED
        assert call_args.ticket_id == 1

    def test_escalated_manual_review_sends_escalation_email(self, workflow_with_email, gmail_service):
        """Should send escalation email when escalating to manual review."""
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

        # Verify escalation email sent
        gmail_service.send_email.assert_called_once()
        call_args = gmail_service.send_email.call_args[0][0]

        # Should be escalation template, not reactivation
        assert call_args.template == EmailTemplate.ESCALATED_MANUAL_REVIEW
        assert call_args.recipient_email == "jane@company.com"

    def test_non_login_issue_does_not_send_email(self, workflow_with_email, gmail_service):
        """Should NOT send email for non-login issues."""
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

        # Verify skipped and no email sent
        assert result.success is True
        assert result.action_taken == "skipped"
        gmail_service.send_email.assert_not_called()

    def test_employee_not_found_sends_escalation_email(self, workflow_with_email, gmail_service):
        """Should send escalation email when employee not found."""
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

        # Verify email sent
        gmail_service.send_email.assert_called_once()
        call_args = gmail_service.send_email.call_args[0][0]
        assert call_args.template == EmailTemplate.ESCALATED_MANUAL_REVIEW

    def test_hr_reactivation_failure_sends_escalation_email(self, workflow_with_email, gmail_service):
        """Should send escalation email when HR reactivation fails."""
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

        # Verify escalation
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"

        # Verify escalation email sent (not success email)
        gmail_service.send_email.assert_called_once()
        call_args = gmail_service.send_email.call_args[0][0]
        assert call_args.template == EmailTemplate.ESCALATED_MANUAL_REVIEW

    def test_email_send_failure_does_not_fail_workflow(self, workflow_with_email, gmail_service):
        """Should continue workflow even if email send fails."""
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

    def test_email_context_includes_employee_details(self, workflow_with_email, gmail_service):
        """Should populate email context with employee details."""
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

        # Verify email context has employee details
        gmail_service.send_email.assert_called_once()
        call_args = gmail_service.send_email.call_args[0][0]

        assert call_args.employee_name == "Alice Brown"
        assert call_args.employee_id == "EMP007"
        assert call_args.department == "Engineering"
        assert call_args.deactivation_reason == DeactivationReason.INACTIVITY_30_DAYS


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
