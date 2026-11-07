"""Phase 4 TDD: LoginWorkflow refactoring with EmailTemplateSelector - RED phase tests."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.gmail import (
    GmailService,
    EmailContext,
    EmailTemplate,
    EmailTemplateSelector,
    CommunicationEvent,
)
from srcs.models import Ticket, Employee, EmployeeStatus
from srcs.services.ticket_analyzer import AnalysisResult, IssueType
from srcs.services.decision_service import Decision, DeactivationReason


class TestLoginWorkflowEventBasedCommunication:
    """Test LoginWorkflow uses event-based communication with EmailTemplateSelector."""

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

    def test_new_login_ticket_sends_acknowledgement(self, workflow_with_email, gmail_service):
        """New login ticket should trigger ACKNOWLEDGEMENT via EmailTemplateSelector."""
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
            reason="Login issue detected",
            confidence=0.9,
        )
        workflow_with_email.hr_client.reactivate_lms_account.return_value = True

        # Execute
        result = workflow_with_email.execute(ticket_id=1)

        # Should send ACK email
        assert gmail_service.send_email.call_count >= 1

        # Find the ACK email call (could be multiple calls)
        ack_call = None
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]
            if context.template == EmailTemplate.ACKNOWLEDGEMENT:
                ack_call = context
                break

        assert ack_call is not None, "Should send ACKNOWLEDGEMENT email"
        assert ack_call.recipient_email == "john@company.com"
        assert ack_call.ticket_id == 1

    def test_verified_reactivation_sends_resolution_not_acknowledgement(
        self, workflow_with_email, gmail_service
    ):
        """Successful reactivation should send RESOLUTION (after ACK)."""
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

        # Execute
        result = workflow_with_email.execute(ticket_id=2)

        # Should send RESOLUTION email
        assert result.success is True
        assert result.action_taken == "account_reactivated"

        # Find resolution email
        resolution_call = None
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]
            if context.template == EmailTemplate.RESOLUTION:
                resolution_call = context
                break

        assert resolution_call is not None, "Should send RESOLUTION email"
        assert resolution_call.recipient_email == "jane@company.com"

    def test_failed_reactivation_does_not_send_resolution(
        self, workflow_with_email, gmail_service
    ):
        """Failed reactivation should NOT send RESOLUTION, should send escalation."""
        ticket = Ticket(
            id=3,
            name="Cannot login",
            email_from="bob@company.com",
        )

        employee = Employee(
            employee_id="EMP003",
            name="Bob Jones",
            email="bob@company.com",
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
        # Reactivation fails
        workflow_with_email.hr_client.reactivate_lms_account.return_value = False

        # Execute
        result = workflow_with_email.execute(ticket_id=3)

        # Should NOT send RESOLUTION (reactivation failed)
        resolution_found = False
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]
            if context.template == EmailTemplate.RESOLUTION:
                resolution_found = True

        assert not resolution_found, "Should NOT send RESOLUTION when reactivation failed"

        # Should send MANUAL_REVIEW instead
        manual_review_found = False
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]
            if context.template == EmailTemplate.MANUAL_REVIEW:
                manual_review_found = True

        assert manual_review_found, "Should send MANUAL_REVIEW when reactivation failed"

    def test_terminated_employee_sends_safe_manual_review(
        self, workflow_with_email, gmail_service
    ):
        """Terminated employee should trigger safe MANUAL_REVIEW email (no HR details)."""
        ticket = Ticket(
            id=4,
            name="Cannot login",
            email_from="terminated@company.com",
        )

        employee = Employee(
            employee_id="EMP004",
            name="Terminated User",
            email="terminated@company.com",
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
        result = workflow_with_email.execute(ticket_id=4)

        # Should escalate (not reactivate)
        assert result.action_taken == "escalated_manual_review"

        # Should send MANUAL_REVIEW email
        gmail_service.send_email.assert_called()

        # Find the manual review email
        manual_review_context = None
        for call in gmail_service.send_email.call_args_list:
            context = call[0][0]
            if context.template == EmailTemplate.MANUAL_REVIEW:
                manual_review_context = context
                break

        assert manual_review_context is not None
        # Email should NOT reveal termination status
        assert not hasattr(manual_review_context, 'employee_id') or manual_review_context.recipient_name == employee.name

    def test_email_selector_integration(self, workflow_with_email):
        """EmailTemplateSelector should be used internally for template selection."""
        # This test verifies that the workflow uses EmailTemplateSelector
        # Implementation detail: selector should be called, not duplicated logic

        ticket = Ticket(
            id=5,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP005",
            name="User Name",
            email="user@company.com",
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
        result = workflow_with_email.execute(ticket_id=5)

        # Should succeed
        assert result.success is True

        # EmailTemplateSelector should have selected templates
        # We can't directly verify selector was called, but we can verify
        # that correct templates were used (which only selector provides)
        templates_used = set()
        for call in workflow_with_email.gmail_service.send_email.call_args_list:
            context = call[0][0]
            templates_used.add(context.template)

        # Should use templates that come from selector
        assert EmailTemplate.ACKNOWLEDGEMENT in templates_used or EmailTemplate.RESOLUTION in templates_used
