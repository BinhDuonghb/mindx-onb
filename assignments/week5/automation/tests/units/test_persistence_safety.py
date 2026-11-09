"""Regression tests for Issue #4: Persistence Safety.

Tests that AutomationExecutor never reports successful processing when required
automation state changes fail to persist in SQLite.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

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


class TestPersistenceSafety:
    """Tests for persistence safety in AutomationExecutor."""

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

    def test_runner_detects_failed_state_save(self, executor, state_repo):
        """Runner detects when state_repo.save() returns False."""
        ticket = Ticket(
            id=7001,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP7001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor
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

        # Mock save to return False (ownership validation failure)
        original_save = state_repo.save
        def mock_save_fails(*args, **kwargs):
            return False

        state_repo.save = mock_save_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Runner should NOT report this as successful
        # Either result["success"] should be False, or successful count should be 0
        # The key is: should not claim persistence succeeded
        assert result["success"] is False or result["successful"] == 0, \
            "Runner should not report success when state_repo.save() returns False"

    def test_runner_handles_state_save_exception(self, executor, state_repo):
        """Runner handles when state_repo.save() raises an exception."""
        ticket = Ticket(
            id=7002,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP7002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor
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

        # Mock save to raise exception
        def mock_save_raises(*args, **kwargs):
            raise sqlite3.DatabaseError("Database locked")

        state_repo.save = mock_save_raises

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Runner should not report success when save raises
        assert result["success"] is False or result["successful"] == 0, \
            "Runner should not report success when state_repo.save() raises exception"

    def test_runner_detects_failed_retry_scheduling(self, executor, state_repo):
        """Runner detects when schedule_retry() returns False."""
        ticket = Ticket(
            id=7003,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP7003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor
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
        executor.ticket_client.add_log.return_value = True
        executor.ticket_client.update_stage.return_value = True
        executor.gmail_service.send_email.return_value = True

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

        # Mock schedule_retry to return False (ownership validation failure)
        original_schedule_retry = state_repo.schedule_retry
        def mock_schedule_retry_fails(*args, **kwargs):
            return False

        state_repo.schedule_retry = mock_schedule_retry_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Runner should not claim retry was scheduled successfully
        # The failed count should indicate failure
        assert result["failed"] > 0, \
            "Runner should record failure when schedule_retry() returns False"

    def test_runner_detects_failed_mark_completed(self, executor, state_repo):
        """Runner detects when mark_completed() returns False."""
        ticket = Ticket(
            id=7004,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP7004",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor
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

        # Mock mark_completed to return False
        original_mark_completed = state_repo.mark_completed
        def mock_mark_completed_fails(*args, **kwargs):
            return False

        state_repo.mark_completed = mock_mark_completed_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Runner should not count this as successful completion
        assert result["successful"] == 0, \
            "Runner should not count ticket as successful when mark_completed() returns False"

    def test_runner_detects_failed_manual_review_transition(self, executor, state_repo):
        """Runner detects when mark_manual_review() returns False."""
        ticket = Ticket(
            id=7005,
            name="Unknown issue",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP7005",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,
            issue_type=None,
            reason="Cannot determine issue",
            confidence=0.1
        )

        workflow_result = WorkflowResult(
            action_taken="escalated_manual_review",
            success=True,
            message="Escalated to manual review",
            reactivation_completed=False,
            odoo_note_completed=False,
            stage_update_completed=False,
            email_delivery_completed=False
        )
        executor.workflow.execute.return_value = workflow_result

        # Mock mark_manual_review to return False
        original_mark_manual_review = state_repo.mark_manual_review
        def mock_mark_manual_review_fails(*args, **kwargs):
            return False

        state_repo.mark_manual_review = mock_mark_manual_review_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Runner should not count this as escalated when transition fails
        assert result["escalated"] == 0, \
            "Runner should not count ticket as escalated when mark_manual_review() returns False"

    def test_runner_detects_failed_skip_transition(self, executor, state_repo):
        """Runner detects when mark_skipped() returns False."""
        ticket = Ticket(
            id=7006,
            name="Already resolved",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP7006",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="active",
            deactivation_reason=None
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )

        workflow_result = WorkflowResult(
            action_taken="skipped",
            success=True,
            message="Employee terminated, skipping",
            reactivation_completed=False,
            odoo_note_completed=False,
            stage_update_completed=False,
            email_delivery_completed=False
        )
        executor.workflow.execute.return_value = workflow_result

        # Mock mark_skipped to return False
        original_mark_skipped = state_repo.mark_skipped
        def mock_mark_skipped_fails(*args, **kwargs):
            return False

        state_repo.mark_skipped = mock_mark_skipped_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Runner should not count this as skipped when transition fails
        # Should be counted as failed instead
        assert result["skipped"] == 0 or result["failed"] > 0, \
            "Runner should not count ticket as skipped when mark_skipped() returns False"
