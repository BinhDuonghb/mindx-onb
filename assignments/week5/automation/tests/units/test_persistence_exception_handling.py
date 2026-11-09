"""Regression tests for Issue #4: Persistence Exception Handling.

Tests that repository exceptions are correctly classified as persistence failures
and result in success=False.
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
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class TestPersistenceExceptionHandling:
    """Tests for persistence exception handling in run_once()."""

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

    def test_schedule_retry_exception_sets_persistence_failure(self, executor, state_repo):
        """When schedule_retry() raises exception, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=10001,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP10001",
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

        # Mock schedule_retry to raise exception
        state_repo.schedule_retry = Mock(side_effect=sqlite3.OperationalError("Database locked"))

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when schedule_retry raises
        assert result["success"] is False, \
            "Result must have success=False when schedule_retry() raises exception"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when schedule_retry raises"

        # VERIFY: error_details includes operation context
        assert any("schedule_retry" in detail for detail in result["error_details"]), \
            "error_details must identify schedule_retry operation"

    def test_mark_completed_exception_sets_persistence_failure(self, executor, state_repo):
        """When mark_completed() raises exception, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=10002,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP10002",
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
        executor.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        executor.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
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

        # Mock mark_completed to raise exception
        state_repo.mark_completed = Mock(side_effect=sqlite3.OperationalError("Disk I/O error"))

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when mark_completed raises
        assert result["success"] is False, \
            "Result must have success=False when mark_completed() raises exception"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when mark_completed raises"

        # VERIFY: error_details includes operation context
        assert any("mark_completed" in detail for detail in result["error_details"]), \
            "error_details must identify mark_completed operation"

    def test_mark_manual_review_exception_sets_persistence_failure(self, executor, state_repo):
        """When mark_manual_review() raises exception, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=10003,
            name="Unknown issue",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP10003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for manual review escalation
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

        # Mock mark_manual_review to raise exception
        state_repo.mark_manual_review = Mock(side_effect=sqlite3.OperationalError("Database corrupt"))

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when mark_manual_review raises
        assert result["success"] is False, \
            "Result must have success=False when mark_manual_review() raises exception"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when mark_manual_review raises"

        # VERIFY: error_details includes operation context
        assert any("mark_manual_review" in detail for detail in result["error_details"]), \
            "error_details must identify mark_manual_review operation"

    def test_mark_skipped_exception_sets_persistence_failure(self, executor, state_repo):
        """When mark_skipped() raises exception, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=10004,
            name="Already resolved",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP10004",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="active",
            deactivation_reason=None
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for skip
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

        # Mock mark_skipped to raise exception
        state_repo.mark_skipped = Mock(side_effect=sqlite3.OperationalError("Connection failed"))

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when mark_skipped raises
        assert result["success"] is False, \
            "Result must have success=False when mark_skipped() raises exception"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when mark_skipped raises"

        # VERIFY: error_details includes operation context
        assert any("mark_skipped" in detail for detail in result["error_details"]), \
            "error_details must identify mark_skipped operation"

    def test_save_exception_sets_persistence_failure(self, executor, state_repo):
        """When _save_ticket_state() save() raises exception, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=10005,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP10005",
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
        executor.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        executor.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
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
        state_repo.save = Mock(side_effect=sqlite3.OperationalError("Database locked"))

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when save raises
        assert result["success"] is False, \
            "Result must have success=False when save() raises exception"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when save raises"

        # VERIFY: error_details includes operation context
        assert any("save" in detail for detail in result["error_details"]), \
            "error_details must identify save operation"

    def test_cli_exit_nonzero_after_persistence_exception(self, executor, state_repo):
        """CLI should exit with nonzero code when persistence exception occurs."""
        ticket = Ticket(
            id=10006,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP10006",
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
        executor.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        executor.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
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

        # Mock mark_completed to raise exception
        state_repo.mark_completed = Mock(side_effect=sqlite3.OperationalError("I/O error"))

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: result["success"] is False (which CLI uses for exit code)
        assert result["success"] is False, \
            "result[\"success\"] must be False for persistence exception"

        # VERIFY: persistence_failures > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0"

        # VERIFY: failed > 0
        assert result["failed"] > 0, \
            "failed count must be > 0"
