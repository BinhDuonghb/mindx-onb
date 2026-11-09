"""Terminal lease release tests for Issue #2.

Tests that successful workflows release their processing leases so changed
tickets can be claimed immediately for reprocessing.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone

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


class TestTerminalLeaseRelease:
    """Tests for lease release after terminal workflow outcomes."""

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
        # Setup mocked poller to handle ticket polling
        executor.poller = Mock()
        executor.poller.poll.return_value = []  # No regular tickets by default
        executor.poller.poll_for_retry.return_value = []  # No retry tickets by default
        executor.metrics = PollingMetrics()
        executor.workflow = Mock()
        # Mock get_expired_processing_tickets to return empty list
        state_repo.get_expired_processing_tickets = Mock(return_value=[])
        return executor

    def test_runner_releases_lease_after_success(self, executor, state_repo):
        """Successful completion releases the processing lease."""
        ticket = Ticket(
            id=5001,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP5001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup mocked poller to return ticket
        executor.poller.poll.return_value = [ticket]
        # Mock get_due_retries to return empty list (no retries scheduled)
        state_repo.get_due_retries = Mock(return_value=[])

        # Setup mocks
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

        # Mock workflow execution
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

        # Run executor (claims and processes ticket)
        result = executor.run_once(limit=10)
        assert result["success"] is True

        # Verify lease is RELEASED after successful completion
        final_state = state_repo.get(5001)
        assert final_state.status == AutomationStatus.COMPLETED
        assert final_state.processing_lease_until is None, "Lease should be released"
        assert final_state.lease_owner_token is None, "Token should be cleared"


    def test_runner_releases_lease_after_manual_review(self, executor, state_repo):
        """Manual review completion releases the processing lease."""
        ticket = Ticket(
            id=5002,
            name="Unknown issue",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP5002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup mocked poller to return ticket
        executor.poller.poll.return_value = [ticket]
        # Mock get_due_retries to return empty list
        state_repo.get_due_retries = Mock(return_value=[])

        # Setup mocks for manual review scenario
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=False,
            issue_type=None,
            reason="Cannot determine issue",
            confidence=0.1
        )

        # Mock workflow execution for manual review
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

        # Run executor
        result = executor.run_once(limit=10)
        assert result["success"] is True

        # Verify lease is released and status is MANUAL_REVIEW
        final_state = state_repo.get(5002)
        assert final_state.status == AutomationStatus.MANUAL_REVIEW
        assert final_state.processing_lease_until is None, "Lease should be released"
        assert final_state.lease_owner_token is None, "Token should be cleared"

    def test_runner_releases_lease_after_skip(self, executor, state_repo):
        """Skipped ticket releases the processing lease."""
        ticket = Ticket(
            id=5003,
            name="Already resolved",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP5003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.TERMINATED,
            lms_account_status="active",
            deactivation_reason=None
        )

        fp = TicketFingerprinter.generate(ticket)

        # Setup mocked poller to return ticket
        executor.poller.poll.return_value = [ticket]
        # Mock get_due_retries to return empty list
        state_repo.get_due_retries = Mock(return_value=[])

        # Setup mocks - employee is terminated so workflow skips
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )

        # Mock workflow execution for skip
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

        # Run executor
        result = executor.run_once(limit=10)
        assert result["success"] is True

        # Verify lease is released and status is SKIPPED
        final_state = state_repo.get(5003)
        assert final_state.status == AutomationStatus.SKIPPED
        assert final_state.processing_lease_until is None, "Lease should be released"
        assert final_state.lease_owner_token is None, "Token should be cleared"

    def test_fingerprint_change_can_claim_after_completion(self, executor, state_repo):
        """Changed ticket can be claimed immediately after completion."""
        ticket = Ticket(
            id=5004,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP5004",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        fp1 = TicketFingerprinter.generate(ticket)

        # Setup mocked poller to return ticket
        executor.poller.poll.return_value = [ticket]
        # Mock get_due_retries to return empty list
        state_repo.get_due_retries = Mock(return_value=[])

        # First run - successful completion
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

        result1 = executor.run_once(limit=10)
        assert result1["success"] is True

        # Verify lease released
        state_after_first = state_repo.get(5004)
        assert state_after_first.processing_lease_until is None

        # Ticket fingerprint changes
        ticket.name = "Cannot login (Updated)"
        fp2 = TicketFingerprinter.generate(ticket)
        assert fp2 != fp1

        # Verify we can immediately claim the changed ticket
        token_new = state_repo.claim_for_processing(
            ticket_id=5004,
            fingerprint=fp2,
            lease_duration_seconds=300
        )
        assert token_new is not None, "Should be able to claim changed ticket immediately after completion"

        new_state = state_repo.get(5004)
        assert new_state.processing_lease_until is not None
        assert new_state.lease_owner_token == token_new

    def test_stale_worker_cannot_release_lease_on_completion(self, executor, state_repo):
        """Stale worker cannot release another worker's lease via completion."""
        ticket = Ticket(
            id=5005,
            name="Cannot login",
            email_from="user@company.com"
        )

        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = state_repo.claim_for_processing(
            ticket_id=5005,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert token_a is not None

        # Manually create a completed state with Worker A's token
        now = datetime.now(timezone.utc)
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE automation_state
                SET status = ?, processing_lease_until = ?, lease_owner_token = ?
                WHERE ticket_id = ?
            """, (
                AutomationStatus.COMPLETED.value,
                (now + timedelta(seconds=300)).isoformat(),
                token_a,
                5005
            ))
            conn.commit()

        # Expire Worker A's lease and Worker B claims
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 5005)
            )
            conn.commit()

        token_b = state_repo.claim_for_processing(
            ticket_id=5005,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert token_b is not None
        assert token_b != token_a

        # Worker A (stale) tries to mark completed with old token (should fail)
        result = state_repo.mark_completed(ticket_id=5005, owner_token=token_a)
        assert result is False, "Stale worker should not be able to release lease"

        # Verify Worker B still owns it
        final_state = state_repo.get(5005)
        assert final_state.lease_owner_token == token_b
        assert final_state.processing_lease_until is not None
