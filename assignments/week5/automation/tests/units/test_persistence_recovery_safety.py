"""Regression tests for Issue #4: Persistence Recovery Safety.

Tests that failed repository transitions preserve recoverable state and don't
leave tickets stranded with incomplete metadata.
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


class TestPersistenceRecoverySafety:
    """Tests for persistence recovery safety."""

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

    def test_failed_retry_scheduling_remains_recoverable(self, executor, state_repo):
        """When schedule_retry() fails, ticket remains PROCESSING and recoverable."""
        ticket = Ticket(
            id=8001,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP8001",
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

        # Mock schedule_retry to fail (ownership validation)
        def mock_schedule_retry_fails(*args, **kwargs):
            return False

        state_repo.schedule_retry = mock_schedule_retry_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Ticket remains PROCESSING (not stuck in RETRY_SCHEDULED)
        final_state = state_repo.get(8001)
        assert final_state.status == AutomationStatus.PROCESSING, \
            "Failed retry scheduling should leave ticket in PROCESSING status, not RETRY_SCHEDULED"

        # VERIFY: next_retry_at should NOT be set
        assert final_state.next_retry_at is None, \
            "Failed transition should not set next_retry_at"

        # VERIFY: Ticket remains discoverable via expired processing recovery
        # Simulate lease expiration
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 8001)
            )
            conn.commit()

        # Restore real method to check recovery
        from srcs.repositories.automation_state_repository import AutomationStateRepository as StateRepo
        real_get_expired = StateRepo.get_expired_processing_tickets
        expired_tickets = real_get_expired(state_repo, limit=10)
        assert len(expired_tickets) == 1, "Failed retry ticket should be discoverable for recovery"
        assert expired_tickets[0].ticket_id == 8001

    def test_failed_mark_completed_remains_recoverable(self, executor, state_repo):
        """When mark_completed() fails, ticket remains PROCESSING and recoverable."""
        ticket = Ticket(
            id=8002,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP8002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for successful completion
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
        def mock_mark_completed_fails(*args, **kwargs):
            return False

        state_repo.mark_completed = mock_mark_completed_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Ticket remains PROCESSING (not transitioned to COMPLETED)
        final_state = state_repo.get(8002)
        assert final_state.status == AutomationStatus.PROCESSING, \
            "Failed mark_completed should leave ticket in PROCESSING status, not COMPLETED"

        # VERIFY: Side effects ARE recorded (preserved)
        assert final_state.reactivation_completed is True
        assert final_state.odoo_note_completed is True
        assert final_state.stage_update_completed is True
        assert final_state.email_delivery_completed is True

        # VERIFY: Lease is still active (mark_completed failed to release it)
        assert final_state.processing_lease_until is not None
        assert final_state.lease_owner_token is not None

    def test_failed_manual_review_remains_recoverable(self, executor, state_repo):
        """When mark_manual_review() fails, ticket remains PROCESSING and recoverable."""
        ticket = Ticket(
            id=8003,
            name="Unknown issue",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP8003",
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

        # Mock mark_manual_review to fail
        def mock_mark_manual_review_fails(*args, **kwargs):
            return False

        state_repo.mark_manual_review = mock_mark_manual_review_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Ticket remains PROCESSING (not transitioned to MANUAL_REVIEW)
        final_state = state_repo.get(8003)
        assert final_state.status == AutomationStatus.PROCESSING, \
            "Failed mark_manual_review should leave ticket in PROCESSING status, not MANUAL_REVIEW"

    def test_failed_mark_skipped_remains_recoverable(self, executor, state_repo):
        """When mark_skipped() fails, ticket remains PROCESSING and recoverable."""
        ticket = Ticket(
            id=8004,
            name="Already resolved",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP8004",
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

        # Mock mark_skipped to fail
        def mock_mark_skipped_fails(*args, **kwargs):
            return False

        state_repo.mark_skipped = mock_mark_skipped_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: Ticket remains PROCESSING (not transitioned to SKIPPED)
        final_state = state_repo.get(8004)
        assert final_state.status == AutomationStatus.PROCESSING, \
            "Failed mark_skipped should leave ticket in PROCESSING status, not SKIPPED"

    def test_persistence_failure_is_distinguishable_in_run_result(self, executor, state_repo):
        """run_once() result clearly indicates persistence failure vs workflow failure."""
        ticket = Ticket(
            id=8005,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP8005",
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

        # VERIFY: Persistence failure is recorded in result counts
        assert result["successful"] == 0, \
            "Should not count as successful when terminal transition fails"

        assert result["failed"] > 0, \
            "Persistence failure must be recorded in failed count"

    def test_recovered_ticket_preserves_completed_side_effects(self, executor, state_repo):
        """Recovered ticket after failed transition preserves completed side effects."""
        ticket = Ticket(
            id=8006,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP8006",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup executor for first attempt (successful but transition fails)
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

        # First call to mark_completed fails
        call_count = [0]
        def mock_mark_completed_first_fails(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # First call fails
            return True  # Subsequent calls succeed

        state_repo.mark_completed = mock_mark_completed_first_fails

        # First run - transition fails
        result1 = executor.run_once(limit=10)
        state_after_failure = state_repo.get(8006)

        # VERIFY: Side effects preserved despite transition failure
        assert state_after_failure.reactivation_completed is True
        assert state_after_failure.odoo_note_completed is True
        assert state_after_failure.stage_update_completed is True
        assert state_after_failure.email_delivery_completed is True

        # Now simulate recovery after lease expiration
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 8006)
            )
            conn.commit()

        # Executor polls expired tickets and reclaims
        from srcs.repositories.automation_state_repository import AutomationStateRepository as StateRepo
        real_get_expired = StateRepo.get_expired_processing_tickets
        state_repo.get_expired_processing_tickets = lambda limit: real_get_expired(state_repo, limit=limit)

        # Second run - recovered ticket, transition now succeeds
        executor.poller.poll.return_value = []  # No new tickets
        result2 = executor.run_once(limit=10)

        # VERIFY: Side effects still preserved during recovery
        state_after_recovery = state_repo.get(8006)
        assert state_after_recovery.reactivation_completed is True, \
            "Recovery should preserve reactivation_completed flag"
        assert state_after_recovery.odoo_note_completed is True, \
            "Recovery should preserve odoo_note_completed flag"
