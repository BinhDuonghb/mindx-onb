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
        """Should send resolution email on successful reactivation (after ACK)."""
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

        # Verify emails were sent (ACK + RESOLUTION)
        assert gmail_service.send_email.call_count >= 1

        # Extract templates from calls
        templates_sent = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]

        # Should include ACKNOWLEDGEMENT and RESOLUTION
        assert EmailTemplate.ACKNOWLEDGEMENT in templates_sent
        assert EmailTemplate.RESOLUTION in templates_sent

        # Verify resolution email has correct context
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]
            if context.template == EmailTemplate.RESOLUTION:
                assert context.recipient_email == "john@company.com"
                assert context.ticket_id == 1

    def test_escalated_manual_review_sends_escalation_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send manual review email when escalating (after ACK)."""
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

        # Verify emails were sent (ACK + MANUAL_REVIEW)
        assert gmail_service.send_email.call_count >= 1

        # Extract templates from calls
        templates_sent = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]

        # Should include ACKNOWLEDGEMENT and MANUAL_REVIEW
        assert EmailTemplate.ACKNOWLEDGEMENT in templates_sent
        assert EmailTemplate.MANUAL_REVIEW in templates_sent

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

    def test_employee_not_found_sends_escalation_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send manual review email when employee not found (after ACK)."""
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

        # Verify emails were sent (ACK + MANUAL_REVIEW)
        assert gmail_service.send_email.call_count >= 1

        # Extract templates from calls
        templates_sent = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]

        assert EmailTemplate.ACKNOWLEDGEMENT in templates_sent
        assert EmailTemplate.MANUAL_REVIEW in templates_sent

    def test_hr_reactivation_failure_sends_escalation_email(
        self, workflow_with_email, gmail_service
    ):
        """Should send manual review email when HR reactivation fails (after ACK)."""
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

        # Verify emails were sent (ACK + MANUAL_REVIEW, not RESOLUTION)
        assert gmail_service.send_email.call_count >= 1

        # Extract templates from calls
        templates_sent = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]

        assert EmailTemplate.ACKNOWLEDGEMENT in templates_sent
        assert EmailTemplate.MANUAL_REVIEW in templates_sent
        # Should NOT send RESOLUTION when reactivation failed
        assert EmailTemplate.RESOLUTION not in templates_sent

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

    def test_email_context_respects_hr_privacy(self, workflow_with_email, gmail_service):
        """Should NOT include HR data in customer emails per Week 4 requirements."""
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

        # Check all email contexts don't include HR data
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]

            # Week 4: EmailContext should NOT have employee_id, department, deactivation_reason
            assert not hasattr(context, 'employee_id')
            assert not hasattr(context, 'department')
            assert not hasattr(context, 'deactivation_reason')

            # But it should have the public fields
            assert context.recipient_email == "alice@company.com"
            assert context.ticket_id == 7


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
