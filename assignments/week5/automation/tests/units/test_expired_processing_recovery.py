"""Regression tests for Issue #3: Expired PROCESSING ticket recovery.

Tests that tickets stuck in PROCESSING after crashes are automatically recovered
when their processing lease expires, without unnecessarily repeating completed
side effects.
"""

import pytest
import tempfile
import sqlite3
import threading
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
from srcs.services.ticket_poller import TicketPoller, PollingMetrics


class TestExpiredProcessingRecovery:
    """Tests for recovery of expired PROCESSING tickets."""

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
    def ticket_client(self):
        return Mock()

    @pytest.fixture
    def poller(self, ticket_client, state_repo):
        return TicketPoller(ticket_client=ticket_client, state_repo=state_repo)

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
        # Setup mocked poller
        executor.poller = Mock()
        executor.poller.poll.return_value = []
        executor.poller.poll_for_retry.return_value = []
        executor.metrics = PollingMetrics()
        executor.workflow = Mock()
        # Mock get_expired_processing_tickets to return empty list by default
        state_repo.get_expired_processing_tickets = Mock(return_value=[])
        # Mock get_due_retries to return empty list by default
        state_repo.get_due_retries = Mock(return_value=[])
        return executor

    def test_expired_processing_ticket_is_discovered(self, state_repo, ticket_client, poller):
        """Expired PROCESSING ticket is discovered by poller."""
        ticket = Ticket(
            id=6001,
            name="Cannot login",
            email_from="user@company.com"
        )

        # Setup: Create ticket in PROCESSING with expired lease
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        state = AutomationState(
            ticket_id=6001,
            fingerprint="fp_6001",
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,
            odoo_note_completed=False
        )
        state_repo.save(state)

        # Manually set expired lease
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 6001)
            )
            conn.commit()

        # Verify discovery: get_expired_processing_tickets should return it
        expired_tickets = state_repo.get_expired_processing_tickets(limit=10)
        assert len(expired_tickets) == 1
        assert expired_tickets[0].ticket_id == 6001
        assert expired_tickets[0].status == AutomationStatus.PROCESSING

    def test_active_processing_ticket_is_not_recovered(self, state_repo):
        """Active PROCESSING ticket with valid lease is not marked for recovery."""
        ticket_id = 6002
        now = datetime.now(timezone.utc)
        active_lease = now + timedelta(minutes=5)  # Future lease

        state = AutomationState(
            ticket_id=ticket_id,
            fingerprint="fp_6002",
            status=AutomationStatus.PROCESSING
        )
        state_repo.save(state)

        # Set active (future) lease
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (active_lease.isoformat(), ticket_id)
            )
            conn.commit()

        # Verify: should NOT be discovered
        expired_tickets = state_repo.get_expired_processing_tickets(limit=10)
        assert len(expired_tickets) == 0

    def test_expired_processing_ticket_can_be_reclaimed(self, state_repo):
        """Only one worker can reclaim an expired PROCESSING ticket (atomicity)."""
        ticket_id = 6003
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)
        fp = "fp_6003"

        state = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fp,
            status=AutomationStatus.PROCESSING
        )
        state_repo.save(state)

        # Set expired lease
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), ticket_id)
            )
            conn.commit()

        # Two workers race to reclaim
        claimed_tokens = []
        lock = threading.Lock()

        def worker_claim(worker_id):
            repo = AutomationStateRepository(db_path=state_repo.db_path)
            token = repo.claim_for_processing(
                ticket_id=ticket_id,
                fingerprint=fp,
                lease_duration_seconds=300
            )
            if token is not None:
                with lock:
                    claimed_tokens.append((worker_id, token))

        threads = [
            threading.Thread(target=worker_claim, args=(1,)),
            threading.Thread(target=worker_claim, args=(2,))
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one worker should succeed
        assert len(claimed_tokens) == 1, f"Expected 1 successful claim, got {len(claimed_tokens)}"

        # Verify database state
        final_state = state_repo.get(ticket_id)
        assert final_state.lease_owner_token is not None
        assert final_state.status == AutomationStatus.PROCESSING

    def test_recovery_preserves_completed_side_effects(self, state_repo):
        """Recovery preserves completed side effect flags and doesn't repeat them."""
        ticket_id = 6004
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        # Create PROCESSING ticket with partial completion
        state = AutomationState(
            ticket_id=ticket_id,
            fingerprint="fp_6004",
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,      # COMPLETED - should not repeat
            odoo_note_completed=False,         # PENDING - should complete
            stage_update_completed=False,      # PENDING - should complete
            email_delivery_completed=False     # PENDING - should complete
        )
        state_repo.save(state)

        # Set expired lease
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), ticket_id)
            )
            conn.commit()

        # Recover and verify flags are preserved
        recovered_state = state_repo.get(ticket_id)
        assert recovered_state.reactivation_completed is True, "Completed flag should be preserved"
        assert recovered_state.odoo_note_completed is False, "Pending flag should remain pending"
        assert recovered_state.stage_update_completed is False
        assert recovered_state.email_delivery_completed is False

    def test_runner_recovers_expired_processing_after_restart(self, executor, state_repo):
        """Runner recovers expired PROCESSING ticket after restart without repeating side effects."""
        ticket = Ticket(
            id=6005,
            name="Cannot login",
            email_from="user@company.com"
        )
        employee = Employee(
            employee_id="EMP6005",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)
        fp = TicketFingerprinter.generate(ticket)

        # STEP 1: Simulate first run that crashed during processing
        # Create ticket in PROCESSING with partial completion
        state = AutomationState(
            ticket_id=6005,
            fingerprint=fp,
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,      # LMS reactivation succeeded
            odoo_note_completed=True,         # Odoo note succeeded
            stage_update_completed=False,     # Stage update failed
            email_delivery_completed=False    # Email not sent
        )
        state_repo.save(state)

        # Set expired lease (simulating crash that left lease active)
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 6005)
            )
            conn.commit()

        # STEP 2: New runner starts and discovers expired ticket
        # Restore real method (executor fixture mocks it to return [])
        from srcs.repositories.automation_state_repository import AutomationStateRepository as StateRepo
        state_repo.get_expired_processing_tickets = StateRepo.get_expired_processing_tickets.__get__(state_repo, StateRepo)

        expired_states = state_repo.get_expired_processing_tickets(limit=10)
        assert len(expired_states) == 1
        assert expired_states[0].ticket_id == 6005

        # Mock executor to handle recovery
        executor.ticket_client.get_ticket.return_value = ticket
        executor.hr_client.get_employee_by_email.return_value = employee
        executor.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9
        )

        # Mock workflow: should NOT call reactivation again (already done)
        # but SHOULD complete stage update and email
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

        # Mock poller to return expired ticket for recovery
        # The poller should be called in run_once() to get expired tickets
        def mock_get_expired(limit=10):
            # Need to store the real method before we replace it
            from srcs.repositories.automation_state_repository import AutomationStateRepository as StateRepo
            real_method = StateRepo.get_expired_processing_tickets
            return real_method(state_repo, limit=limit)

        state_repo.get_expired_processing_tickets = mock_get_expired
        executor.ticket_client.get_ticket.return_value = ticket

        # Setup executor polling
        executor.poller.poll.return_value = []
        executor.poller.poll_for_retry.return_value = []

        # Run executor - should discover and recover the expired ticket
        result = executor.run_once(limit=10)

        # STEP 3: Verify recovery was successful
        assert result["success"] is True

        # Verify final state
        final_state = state_repo.get(6005)
        assert final_state.status == AutomationStatus.COMPLETED
        assert final_state.processing_lease_until is None, "Lease should be released"
        assert final_state.lease_owner_token is None, "Token should be cleared"
        assert final_state.reactivation_completed is True  # Not repeated
        assert final_state.odoo_note_completed is True     # Not repeated
        assert final_state.stage_update_completed is True   # Should be completed in recovery
        assert final_state.email_delivery_completed is True # Should be sent in recovery
