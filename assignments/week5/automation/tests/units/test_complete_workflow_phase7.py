"""Phase 7 TDD: Comprehensive workflow tests - RED phase tests."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.gmail import GmailService, EmailTemplate, CommunicationEvent
from srcs.services.communication_state import CommunicationStateTracker
from srcs.models import Ticket, Employee, EmployeeStatus
from srcs.services.ticket_analyzer import AnalysisResult, IssueType
from srcs.services.decision_service import DeactivationReason


class TestCompleteWorkflowLifecycle:
    """Test complete workflow from ticket received to confirmation."""

    @pytest.fixture
    def setup(self):
        """Setup workflow with all dependencies."""
        gmail_service = Mock(spec=GmailService)
        gmail_service.send_email = Mock(return_value=True)

        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
        )

        return {
            'workflow': workflow,
            'gmail_service': gmail_service,
            'communication_state': workflow.communication_state,
        }

    def test_successful_reactivation_complete_lifecycle(self, setup):
        """Test complete successful workflow: RESOLUTION → CONFIRMATION.

        Phase 1 Communication Policy: Send exactly one email per cycle.
        Success path sends only RESOLUTION (no ACK).
        """
        ticket = Ticket(
            id=100,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP100",
            name="Test User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        setup['workflow'].ticket_client.get_ticket.return_value = ticket
        setup['workflow'].hr_client.get_employee_by_email.return_value = employee
        setup['workflow'].ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )
        setup['workflow'].hr_client.reactivate_lms_account.return_value = True

        # STEP 1: First execution - Send RESOLUTION only
        result1 = setup['workflow'].execute(ticket_id=100)
        assert result1.success is True
        assert result1.action_taken == "account_reactivated"

        # Verify EXACTLY ONE email sent (RESOLUTION only)
        templates_sent_1 = [
            call[0][0].template for call in setup['gmail_service'].send_email.call_args_list
        ]
        assert len(templates_sent_1) == 1
        assert EmailTemplate.RESOLUTION in templates_sent_1

        # Verify state tracking
        assert setup['communication_state'].should_send(
            ticket_id=100, event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        ) is False  # Already sent

        # STEP 2: Re-poll - Should NOT resend RESOLUTION
        setup['gmail_service'].send_email.reset_mock()
        result2 = setup['workflow'].execute(ticket_id=100)
        assert result2.success is True

        templates_sent_2 = [
            call[0][0].template for call in setup['gmail_service'].send_email.call_args_list
        ]
        # Should be empty (no duplicate emails)
        assert len(templates_sent_2) == 0

        # STEP 3: Customer confirms resolution
        setup['communication_state'].mark_confirmed(
            ticket_id=100,
            confirmed_at=datetime.now(timezone.utc)
        )

        # Verify confirmation recorded
        assert setup['communication_state'].is_confirmed(ticket_id=100)

    def test_escalation_complete_lifecycle(self, setup):
        """Test complete escalation workflow: MANUAL_REVIEW.

        Phase 1 Communication Policy: Send exactly one email per cycle.
        Escalation path sends only MANUAL_REVIEW (no ACK).
        """
        ticket = Ticket(
            id=101,
            name="Cannot login",
            email_from="terminated@company.com",
        )

        employee = Employee(
            employee_id="EMP101",
            name="Terminated User",
            email="terminated@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.EMPLOYEE_TERMINATED,
        )

        setup['workflow'].ticket_client.get_ticket.return_value = ticket
        setup['workflow'].hr_client.get_employee_by_email.return_value = employee
        setup['workflow'].ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )

        # STEP 1: First execution - Send MANUAL_REVIEW only
        result1 = setup['workflow'].execute(ticket_id=101)
        assert result1.success is True
        assert result1.action_taken == "escalated_manual_review"

        templates_sent_1 = [
            call[0][0].template for call in setup['gmail_service'].send_email.call_args_list
        ]
        assert len(templates_sent_1) == 1
        assert EmailTemplate.MANUAL_REVIEW in templates_sent_1

        # STEP 2: Re-poll - Should NOT resend
        setup['gmail_service'].send_email.reset_mock()
        result2 = setup['workflow'].execute(ticket_id=101)
        assert result2.success is True

        templates_sent_2 = [
            call[0][0].template for call in setup['gmail_service'].send_email.call_args_list
        ]
        assert len(templates_sent_2) == 0  # No duplicates


class TestMultipleTicketsIndependent:
    """Test that multiple tickets don't interfere with each other."""

    def test_two_tickets_separate_states(self):
        """Each ticket should have independent email state.

        Phase 1 Communication Policy: Each ticket tracks its own email state.
        """
        gmail_service = Mock(spec=GmailService)
        gmail_service.send_email = Mock(return_value=True)

        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
        )

        # Setup ticket 1
        ticket1 = Ticket(id=200, name="Issue 1", email_from="user1@company.com")
        employee1 = Employee(
            employee_id="EMP200",
            name="User 1",
            email="user1@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Setup ticket 2
        ticket2 = Ticket(id=201, name="Issue 2", email_from="user2@company.com")
        employee2 = Employee(
            employee_id="EMP201",
            name="User 2",
            email="user2@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Configure mocks for ticket 1
        workflow.ticket_client.get_ticket.side_effect = lambda tid: ticket1 if tid == 200 else ticket2
        workflow.hr_client.get_employee_by_email.side_effect = lambda email: (
            employee1 if email == "user1@company.com" else employee2
        )
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Issue detected",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # Process ticket 1 - sends RESOLUTION
        result1 = workflow.execute(ticket_id=200)
        assert result1.success is True

        # Verify ticket 1 sent RESOLUTION
        templates_sent_1 = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]
        assert EmailTemplate.RESOLUTION in templates_sent_1

        # Process ticket 2 - should send RESOLUTION (independent state)
        gmail_service.send_email.reset_mock()
        result2 = workflow.execute(ticket_id=201)
        assert result2.success is True

        # Ticket 2 should send RESOLUTION (not affected by ticket 1)
        templates_sent_2 = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]
        assert EmailTemplate.RESOLUTION in templates_sent_2

        # Verify independent states
        assert not workflow.communication_state.should_send(
            ticket_id=200, event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        )  # Ticket 1 already sent
        assert not workflow.communication_state.should_send(
            ticket_id=201, event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        )  # Ticket 2 just sent

        # Confirm ticket 1
        workflow.communication_state.mark_confirmed(
            ticket_id=200, confirmed_at=datetime.now(timezone.utc)
        )

        # Ticket 2 should still be unconfirmed
        assert workflow.communication_state.is_confirmed(ticket_id=200)
        assert not workflow.communication_state.is_confirmed(ticket_id=201)


class TestFollowUpReminderIntegration:
    """Test follow-up reminder as part of complete workflow."""

    def test_follow_up_eligible_after_resolution(self):
        """After RESOLUTION sent, FOLLOW_UP should be eligible.

        Phase 1: Only RESOLUTION is sent (not ACK), so FOLLOW_UP becomes eligible.
        """
        gmail_service = Mock(spec=GmailService)
        gmail_service.send_email = Mock(return_value=True)

        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
        )

        ticket = Ticket(id=300, name="Issue", email_from="user@company.com")
        employee = Employee(
            employee_id="EMP300",
            name="User",
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
            reason="Issue detected",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # Execute workflow (sends RESOLUTION only)
        result = workflow.execute(ticket_id=300)
        assert result.success is True

        # After RESOLUTION sent, FOLLOW_UP should be eligible
        assert workflow.communication_state.should_send(
            ticket_id=300, event=CommunicationEvent.FOLLOW_UP_REMINDER
        )

        # After sending FOLLOW_UP, should not be eligible again
        workflow.communication_state.mark_sent(
            ticket_id=300, event=CommunicationEvent.FOLLOW_UP_REMINDER
        )
        assert not workflow.communication_state.should_send(
            ticket_id=300, event=CommunicationEvent.FOLLOW_UP_REMINDER
        )


class TestFailurePaths:
    """Test error handling and failure paths."""

    def test_email_failure_does_not_break_workflow(self):
        """Email send failure should not prevent account reactivation."""
        gmail_service = Mock(spec=GmailService)
        gmail_service.send_email = Mock(return_value=False)  # Email fails

        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
        )

        ticket = Ticket(id=400, name="Issue", email_from="user@company.com")
        employee = Employee(
            employee_id="EMP400",
            name="User",
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
            reason="Issue detected",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True

        # Execute - should succeed despite email failures
        result = workflow.execute(ticket_id=400)
        assert result.success is True
        assert result.action_taken == "account_reactivated"

    def test_non_login_issue_acknowledgement_only(self):
        """Non-login issues should send no email (skipped).

        Phase 1 Communication Policy: Skip non-login issues without customer notification.
        """
        gmail_service = Mock(spec=GmailService)
        gmail_service.send_email = Mock(return_value=True)

        workflow = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=gmail_service,
        )

        ticket = Ticket(id=401, name="General question", email_from="user@company.com")

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,
            issue_type=None,
            reason="Not a login issue",
            confidence=0.85,
        )

        # Execute
        result = workflow.execute(ticket_id=401)
        assert result.success is True
        assert result.action_taken == "skipped"

        # No emails sent for skipped tickets
        templates_sent = [
            call[0][0].template for call in gmail_service.send_email.call_args_list
        ]
        assert len(templates_sent) == 0
