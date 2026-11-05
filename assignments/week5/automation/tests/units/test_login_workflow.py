"""Integration tests for LoginWorkflow - Complete automation workflow orchestration."""

import pytest
from unittest.mock import Mock, MagicMock
from srcs.services.login_workflow import LoginWorkflow, WorkflowResult
from srcs.models import Ticket, Employee, EmployeeStatus
from srcs.services.ticket_analyzer import AnalysisResult, IssueType
from srcs.services.decision_service import Decision


@pytest.fixture
def mock_ticket_client():
    """Mock Odoo ticket client."""
    client = Mock()
    client.add_log = Mock(return_value=True)
    return client


@pytest.fixture
def mock_hr_client():
    """Mock HR client."""
    client = Mock()
    client.get_employee_by_email = Mock(return_value=None)
    client.reactivate_lms_account = Mock(return_value=True)
    return client


@pytest.fixture
def mock_analyzer():
    """Mock ticket analyzer."""
    analyzer = Mock()
    analyzer.analyze = Mock()
    return analyzer


@pytest.fixture
def workflow(mock_ticket_client, mock_hr_client, mock_analyzer):
    """Create LoginWorkflow with mocked dependencies."""
    return LoginWorkflow(
        ticket_client=mock_ticket_client,
        hr_client=mock_hr_client,
        ticket_analyzer=mock_analyzer,
    )


class TestLoginWorkflowSuccessfulReactivation:
    """Test successful account reactivation flow."""

    def test_active_employee_login_issue_approved_and_executed(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Should successfully reactivate account for active employee with login issue."""
        # Setup ticket
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="john@company.com",
        )

        # Setup employee
        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason="inactivity_30_days",
        )

        # Setup mocks
        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected 'cannot login' pattern",
            confidence=0.95,
        )
        mock_hr_client.reactivate_lms_account.return_value = True

        # Execute workflow
        result = workflow.execute(ticket_id=1)

        # Verify result
        assert result.success is True
        assert result.action_taken == "account_reactivated"
        assert result.ticket_id == 1
        assert result.employee_id == "EMP001"

        # Verify HR status was updated
        mock_hr_client.reactivate_lms_account.assert_called_once_with(
            employee_id="EMP001",
            new_status="active",
        )

        # Verify internal note was posted
        mock_ticket_client.add_log.assert_called_once()
        call_args = mock_ticket_client.add_log.call_args
        assert call_args[1]["ticket_id"] == 1
        assert call_args[1]["is_internal"] is True
        assert "reactivated" in call_args[1]["log_message"].lower()

    def test_workflow_posts_internal_note_on_success(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Should post internal note to ticket on successful reactivation."""
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
            deactivation_reason="inactivity_30_days",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.ACCOUNT_LOCKED,
            reason="Detected 'account locked' pattern",
            confidence=0.9,
        )

        # Execute workflow
        result = workflow.execute(ticket_id=2)

        # Verify success
        assert result.success is True

        # Verify internal note was posted with correct parameters
        mock_ticket_client.add_log.assert_called_once()
        call_kwargs = mock_ticket_client.add_log.call_args[1]
        assert call_kwargs["is_internal"] is True
        assert "Jane Smith" in call_kwargs["log_message"]


class TestLoginWorkflowEscalation:
    """Test escalation flows."""

    def test_terminated_employee_escalated_for_manual_review(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Terminated employee should be escalated for manual review."""
        ticket = Ticket(
            id=3,
            name="Cannot login",
            email_from="terminated@company.com",
        )

        employee = Employee(
            employee_id="EMP003",
            name="Terminated Employee",
            email="terminated@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="deactivated",
            deactivation_reason="Employee terminated",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )

        # Execute workflow
        result = workflow.execute(ticket_id=3)

        # Verify escalation
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"
        assert "terminated" in result.message.lower() or "manual" in result.message.lower()

        # Should NOT update HR status
        mock_hr_client.reactivate_lms_account.assert_not_called()

        # Should post internal note indicating escalation
        mock_ticket_client.add_log.assert_called_once()
        call_kwargs = mock_ticket_client.add_log.call_args[1]
        assert "escalated" in call_kwargs["log_message"].lower()

    def test_employee_not_found_escalated(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Employee not found should be escalated."""
        ticket = Ticket(
            id=4,
            name="Cannot login",
            email_from="unknown@company.com",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = None
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )

        # Execute workflow
        result = workflow.execute(ticket_id=4)

        # Verify escalation
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"
        assert result.employee_id is None

    def test_on_leave_employee_escalated(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """On-leave employee should be escalated."""
        ticket = Ticket(
            id=5,
            name="Cannot login",
            email_from="onleave@company.com",
        )

        employee = Employee(
            employee_id="EMP005",
            name="Employee On Leave",
            email="onleave@company.com",
            status=EmployeeStatus.ON_LEAVE,
            lms_account_status="suspended",
            deactivation_reason="On leave",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )

        # Execute workflow
        result = workflow.execute(ticket_id=5)

        # Verify escalation
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"

    def test_hr_update_failure_escalated(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Should escalate when HR update fails."""
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
            deactivation_reason="inactivity_30_days",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )
        mock_hr_client.reactivate_lms_account.return_value = False

        # Execute workflow
        result = workflow.execute(ticket_id=6)

        # Should escalate on HR failure
        assert result.success is True
        assert result.action_taken == "escalated_manual_review"
        assert "HR" in result.message or "update" in result.message


class TestLoginWorkflowSkip:
    """Test skip flows."""

    def test_non_login_issue_skipped(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Non-login issues should be skipped."""
        ticket = Ticket(
            id=7,
            name="General question",
            email_from="bob@company.com",
        )

        employee = Employee(
            employee_id="EMP007",
            name="Bob Johnson",
            email="bob@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None,
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,
            issue_type=None,
            reason="No login issue pattern detected",
            confidence=0.85,
        )

        # Execute workflow
        result = workflow.execute(ticket_id=7)

        # Verify skipped
        assert result.success is True
        assert result.action_taken == "skipped"
        assert "not a login issue" in result.message.lower()

        # Should NOT update HR or post note
        mock_hr_client.reactivate_lms_account.assert_not_called()
        mock_ticket_client.add_log.assert_not_called()


class TestLoginWorkflowErrorHandling:
    """Test error handling."""

    def test_ticket_not_found(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Should handle ticket not found."""
        mock_ticket_client.get_ticket.return_value = None

        # Execute workflow
        result = workflow.execute(ticket_id=999)

        # Verify error
        assert result.success is False
        assert result.action_taken == "error"
        assert "not found" in result.error_message.lower()
        assert result.ticket_id == 999

    def test_workflow_exception_handling(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Should handle exceptions gracefully."""
        mock_ticket_client.get_ticket.side_effect = Exception("Database error")

        # Execute workflow
        result = workflow.execute(ticket_id=10)

        # Verify error
        assert result.success is False
        assert result.action_taken == "error"
        assert result.error_message is not None

    def test_analyzer_exception_handled(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Should handle analyzer exceptions."""
        ticket = Ticket(
            id=11,
            name="Cannot login",
            email_from="user@company.com",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_analyzer.analyze.side_effect = Exception("Analysis error")

        # Execute workflow
        result = workflow.execute(ticket_id=11)

        # Verify error handled gracefully
        assert result.success is False
        assert result.error_message is not None


class TestLoginWorkflowResultStructure:
    """Test result structure and fields."""

    def test_result_has_all_required_fields(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Result should have all required fields."""
        ticket = Ticket(
            id=12,
            name="Cannot login",
            email_from="john@company.com",
        )

        employee = Employee(
            employee_id="EMP012",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None,
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected login issue",
            confidence=0.9,
        )

        # Execute workflow
        result = workflow.execute(ticket_id=12)

        # Verify all fields present
        assert hasattr(result, "success")
        assert hasattr(result, "action_taken")
        assert hasattr(result, "message")
        assert hasattr(result, "error_message")
        assert hasattr(result, "ticket_id")
        assert hasattr(result, "employee_id")

        # Verify values are set correctly
        assert isinstance(result.success, bool)
        assert isinstance(result.action_taken, str)
        assert isinstance(result.message, str)
        assert result.ticket_id == 12

    def test_result_action_taken_values(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Verify all possible action_taken values."""
        # Test SKIP
        ticket = Ticket(id=1, name="Test", email_from="user@company.com")
        mock_ticket_client.get_ticket.return_value = ticket
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,
            reason="Not a login issue",
            confidence=0.9,
        )

        result = workflow.execute(ticket_id=1)
        assert result.action_taken in ["skipped", "account_reactivated", "escalated_manual_review", "error"]


class TestLoginWorkflowIntegration:
    """Test complete workflow integration."""

    def test_complete_reactivation_workflow(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Test complete reactivation workflow from start to finish."""
        # Setup all mocks
        ticket = Ticket(
            id=20,
            name="Cannot access my account",
            email_from="alice@company.com",
            description="I've been away for a month and can't login",
        )

        employee = Employee(
            employee_id="EMP020",
            name="Alice Brown",
            email="alice@company.com",
            status=EmployeeStatus.ACTIVE,
            department="Sales",
            lms_account_status="deactivated",
            deactivation_reason="inactivity_30_days",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Detected 'cannot access' pattern",
            confidence=0.92,
        )
        mock_hr_client.reactivate_lms_account.return_value = True

        # Execute complete workflow
        result = workflow.execute(ticket_id=20)

        # Verify complete success
        assert result.success is True
        assert result.action_taken == "account_reactivated"
        assert result.ticket_id == 20
        assert result.employee_id == "EMP020"
        assert "alice" in result.message.lower()

        # Verify all steps were executed
        mock_ticket_client.get_ticket.assert_called_once_with(20)
        mock_analyzer.analyze.assert_called_once()
        mock_hr_client.get_employee_by_email.assert_called_once_with("alice@company.com")
        mock_hr_client.reactivate_lms_account.assert_called_once()
        mock_ticket_client.add_log.assert_called_once()

    def test_workflow_decision_flow_active_with_login_issue(
        self, workflow, mock_ticket_client, mock_hr_client, mock_analyzer
    ):
        """Verify decision flow: active employee + login issue = approval."""
        ticket = Ticket(
            id=30,
            name="Account locked",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP030",
            name="User Name",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason="inactivity_30_days",
        )

        mock_ticket_client.get_ticket.return_value = ticket
        mock_hr_client.get_employee_by_email.return_value = employee
        mock_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.ACCOUNT_LOCKED,
            reason="Detected 'account locked' pattern",
            confidence=0.95,
        )

        result = workflow.execute(ticket_id=30)

        # Should be approved because: active + login issue + email match
        assert result.success is True
        assert result.action_taken == "account_reactivated"
