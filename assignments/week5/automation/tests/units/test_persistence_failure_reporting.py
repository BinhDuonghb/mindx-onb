"""Regression tests for Issue #4: Persistence Failure Reporting.

Tests that failed repository persistence operations result in success=False
and are clearly reported in the run result.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from srcs.main import AutomationExecutor
from srcs.models import (
    AutomationState, AutomationStatus, Ticket, Employee,
    EmployeeStatus, DeactivationReason
)
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import WorkflowResult
from srcs.services.ticket_poller import PollingMetrics


class TestPersistenceFailureReporting:
    """Tests for persistence failure reporting in run_once()."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        import os
        os.close(fd)
        yield Path(path)
        if Path(path).exists():
            try:
                Path(path).unlink()
            except:
                pass

    @pytest.fixture
    def state_repo(self, temp_db):
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def executor(self, state_repo):
        """Create AutomationExecutor with mocked dependencies."""
        executor = AutomationExecutor(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo
        )
        executor.poller = Mock()
        executor.poller.poll.return_value = []
        executor.poller.poll_for_retry.return_value = []
        executor.metrics = PollingMetrics()
        executor.workflow = Mock()
        state_repo.get_expired_processing_tickets = Mock(return_value=[])
        state_repo.get_due_retries = Mock(return_value=[])
        return executor

    def test_failed_save_sets_persistence_failure_result(self, executor, state_repo):
        """When _save_ticket_state() fails, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=9001,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP9001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for successful workflow
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )
        executor.hr_client.reactivate_lms_account.return_value = True
        executor.ticket_client.add_log.return_value = True
        executor.ticket_client.update_stage.return_value = True
        executor.gmail_service.send_email.return_value = True

        workflow_result = WorkflowResult(
            action_taken="account_reactivated",
            success=True,
            message="Account reactivated",
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True,
            email_delivery_completed=True
        )
        executor.workflow.execute.return_value = workflow_result

        # Mock save to fail
        state_repo.save = Mock(return_value=False)

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when save fails
        assert result["success"] is False, \
            "Result must have success=False when _save_ticket_state() fails"

        # VERIFY: persistence_failures counter exists and > 0
        assert "persistence_failures" in result, \
            "Result must include persistence_failures counter"
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when save fails"

        # VERIFY: Includes error details
        assert "error_details" in result, \
            "Result must include error_details with operation info"

    def test_failed_retry_transition_sets_persistence_failure_result(self, executor, state_repo):
        """When schedule_retry() fails, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=9002,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP9002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for workflow requiring retry
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )
        executor.hr_client.reactivate_lms_account.return_value = False  # Fail

        workflow_result = WorkflowResult(
            action_taken="retry_scheduled",
            success=False,
            message="LMS reactivation failed",
            error_message="LMS reactivation failed",
            reactivation_completed=False,
            odoo_note_completed=False,
            stage_update_completed=False,
            email_delivery_completed=False
        )
        executor.workflow.execute.return_value = workflow_result

        # Mock schedule_retry to fail (persistence failure)
        state_repo.schedule_retry = Mock(return_value=False)

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when schedule_retry fails
        assert result["success"] is False, \
            "Result must have success=False when schedule_retry() fails"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when schedule_retry fails"

    def test_failed_terminal_transition_sets_persistence_failure_result(self, executor, state_repo):
        """When mark_completed() fails, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=9003,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP9003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for successful workflow
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )
        executor.hr_client.reactivate_lms_account.return_value = True
        executor.ticket_client.add_log.return_value = True
        executor.ticket_client.update_stage.return_value = True
        executor.gmail_service.send_email.return_value = True

        workflow_result = WorkflowResult(
            action_taken="account_reactivated",
            success=True,
            message="Account reactivated",
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True,
            email_delivery_completed=True
        )
        executor.workflow.execute.return_value = workflow_result

        # Mock mark_completed to fail (persistence failure)
        state_repo.mark_completed = Mock(return_value=False)

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when mark_completed fails
        assert result["success"] is False, \
            "Result must have success=False when mark_completed() fails"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when mark_completed fails"

    def test_normal_workflow_retry_is_not_persistence_failure(self, executor, state_repo):
        """Scheduled business retry (workflow failure) is not a persistence failure."""
        ticket = Ticket(
            id=9004,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP9004",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for workflow failure requiring retry
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )
        executor.hr_client.reactivate_lms_account.return_value = False  # Fail

        workflow_result = WorkflowResult(
            action_taken="retry_scheduled",
            success=False,
            message="LMS reactivation failed",
            error_message="LMS reactivation failed",
            reactivation_completed=False,
            odoo_note_completed=False,
            stage_update_completed=False,
            email_delivery_completed=False
        )
        executor.workflow.execute.return_value = workflow_result

        # schedule_retry succeeds (persistence succeeds)
        state_repo.schedule_retry = Mock(return_value=True)

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=True when retry scheduling succeeds (even though workflow failed)
        assert result["success"] is True, \
            "success=True when workflow fails but retry is persisted successfully"

        # VERIFY: persistence_failures is 0
        assert result.get("persistence_failures", 0) == 0, \
            "persistence_failures must be 0 for normal retry scenario"

        # VERIFY: failed count incremented (workflow failure, not persistence failure)
        assert result["failed"] > 0, \
            "failed count should be > 0 for workflow failure"

    def test_successful_processing_has_zero_persistence_failures(self, executor, state_repo):
        """Successful processing with all operations persisted has zero persistence failures."""
        ticket = Ticket(
            id=9005,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP9005",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for successful workflow
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )
        executor.hr_client.reactivate_lms_account.return_value = True
        executor.ticket_client.add_log.return_value = True
        executor.ticket_client.update_stage.return_value = True
        executor.gmail_service.send_email.return_value = True

        workflow_result = WorkflowResult(
            action_taken="account_reactivated",
            success=True,
            message="Account reactivated",
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True,
            email_delivery_completed=True
        )
        executor.workflow.execute.return_value = workflow_result

        # All persistence operations succeed
        state_repo.mark_completed = Mock(return_value=True)

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=True
        assert result["success"] is True, \
            "success=True for completely successful processing"

        # VERIFY: persistence_failures is 0
        assert result.get("persistence_failures", 0) == 0, \
            "persistence_failures must be 0 for successful processing"

        # VERIFY: successful count incremented
        assert result["successful"] > 0, \
            "successful count should be > 0"

    def test_cli_returns_nonzero_exit_on_persistence_failure(self, executor, state_repo):
        """CLI should return nonzero exit code when persistence fails."""
        ticket = Ticket(
            id=9006,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP9006",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for successful workflow
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )
        executor.hr_client.reactivate_lms_account.return_value = True
        executor.ticket_client.add_log.return_value = True
        executor.ticket_client.update_stage.return_value = True
        executor.gmail_service.send_email.return_value = True

        workflow_result = WorkflowResult(
            action_taken="account_reactivated",
            success=True,
            message="Account reactivated",
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True,
            email_delivery_completed=True
        )
        executor.workflow.execute.return_value = workflow_result

        # Mock mark_completed to fail
        state_repo.mark_completed = Mock(return_value=False)

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: result["success"] is False (which CLI will use for exit code)
        assert result["success"] is False, \
            "Result success=False indicates CLI should return nonzero exit code"

        # VERIFY: result includes persistence failure indicator
        assert result.get("persistence_failures", 0) > 0, \
            "Result must clearly indicate persistence failure occurred"
