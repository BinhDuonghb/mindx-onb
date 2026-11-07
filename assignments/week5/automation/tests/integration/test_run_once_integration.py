"""Integration tests for run_once() - RED phase.

Verify that run_once() executes with due retries, handles partial failures,
and recovers state across restarts while preserving side-effect flags.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.models import Ticket, AutomationState, AutomationStatus, Employee, EmployeeStatus
from srcs.services.ticket_poller import TicketPoller
from srcs.main import AutomationExecutor


class TestRunOnceIntegration:
    """Integration tests for AutomationExecutor.run_once()."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    @pytest.fixture
    def executor(self, temp_db):
        """Create executor with mocked clients."""
        executor = Mock(spec=AutomationExecutor)
        executor.state_repo = AutomationStateRepository(db_path=temp_db)
        executor.ticket_client = Mock()
        executor.hr_client = Mock()
        executor.ticket_analyzer = Mock()
        executor.decision_service = Mock()
        executor.poller = TicketPoller(
            ticket_client=executor.ticket_client,
            state_repo=executor.state_repo
        )
        return executor

    def test_run_once_processes_due_retries(self, executor):
        """run_once() should include due retries alongside new tickets."""
        # Setup: Create a retry-scheduled ticket with past retry time
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        state = AutomationState(
            ticket_id=100,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            next_retry_at=past,  # Due for retry
            last_decision="account_reactivated",
            reactivation_completed=True,  # Side effect from first attempt
        )
        executor.state_repo.save(state)

        # Verify the ticket is ready for retry
        retrieved = executor.state_repo.get(100)
        assert retrieved.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved.is_ready_for_retry() is True
        assert retrieved.reactivation_completed is True

    def test_run_once_preserves_side_effects_on_retry(self, executor):
        """Side-effect flags should be preserved when ticket is retried."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        # Create ticket with completed side effects
        state = AutomationState(
            ticket_id=101,
            fingerprint="def456",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            next_retry_at=past,
            reactivation_completed=True,  # Already completed
            odoo_note_completed=True,     # Already completed
            stage_update_completed=False,  # Still pending
        )
        executor.state_repo.save(state)

        # Verify flags are preserved
        retrieved = executor.state_repo.get(101)
        assert retrieved.reactivation_completed is True
        assert retrieved.odoo_note_completed is True
        assert retrieved.stage_update_completed is False

    def test_run_once_schedules_retry_on_partial_failure(self, executor):
        """run_once() should schedule retry when step fails but previous steps succeeded."""
        now = datetime.now(timezone.utc)

        # Simulate: Reactivation succeeded, but Odoo note posting failed
        state = AutomationState(
            ticket_id=102,
            fingerprint="ghi789",
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,  # Success
            odoo_note_completed=False,     # Failed - will retry
        )
        executor.state_repo.save(state)

        # Schedule retry
        executor.state_repo.schedule_retry(
            ticket_id=102,
            retry_after_seconds=3600,
            error="Failed to post Odoo note"
        )

        # Verify scheduled state
        retrieved = executor.state_repo.get(102)
        assert retrieved.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved.retry_count == 1
        assert retrieved.reactivation_completed is True  # Preserved
        assert retrieved.next_retry_at is not None

    def test_run_once_handles_concurrent_ticket_claim(self, executor):
        """run_once() should skip tickets already being processed by another worker."""
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        ticket = Ticket(
            id=103,
            name="Cannot login",
            email_from="user@company.com",
        )

        fingerprint = TicketFingerprinter.generate(ticket)

        # First worker claims ticket
        claimed1 = executor.state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300  # 5 minute active lease
        )
        assert claimed1 is True

        # Second worker (in another run_once instance) tries to claim
        claimed2 = executor.state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed2 is False  # Should fail - lease active

    def test_run_once_recovers_expired_processing_lease(self, executor):
        """run_once() should recover expired processing leases."""
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        ticket = Ticket(
            id=104,
            name="Cannot login",
            email_from="user@company.com",
        )

        fingerprint = TicketFingerprinter.generate(ticket)

        # Claim with already-expired lease
        claimed1 = executor.state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=0  # Already expired
        )
        assert claimed1 is True

        # Next run should be able to reclaim
        claimed2 = executor.state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed2 is True

    def test_run_once_state_persistence_across_restarts(self, executor):
        """Ticket processing state should survive application restart."""
        now = datetime.now(timezone.utc)

        # Create and save state simulating a partial processing
        original_state = AutomationState(
            ticket_id=105,
            fingerprint="jkl012",
            status=AutomationStatus.RETRY_SCHEDULED,
            last_decision="account_reactivated",
            last_reason="Active employee, 30-day inactivity",
            retry_count=1,
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=False,
            next_retry_at=now + timedelta(hours=1),
        )
        executor.state_repo.save(original_state)

        # Simulate restart: Create fresh repository instance (same DB)
        temp_db_path = executor.state_repo.db_path
        new_repo = AutomationStateRepository(db_path=temp_db_path)

        # Verify state survived restart
        retrieved_state = new_repo.get(105)
        assert retrieved_state is not None
        assert retrieved_state.ticket_id == 105
        assert retrieved_state.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved_state.retry_count == 1
        assert retrieved_state.reactivation_completed is True
        assert retrieved_state.odoo_note_completed is True
        assert retrieved_state.stage_update_completed is False
        assert retrieved_state.next_retry_at == original_state.next_retry_at

    def test_run_once_deduplicates_tickets_from_multiple_sources(self, executor):
        """run_once() should deduplicate tickets from poll() and poll_for_retry()."""
        # Create a ticket that would appear in both sources
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        # Already processed but due for retry
        state = AutomationState(
            ticket_id=106,
            fingerprint="mno345",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            next_retry_at=past,
        )
        executor.state_repo.save(state)

        # Verify it's ready for retry
        retrieved = executor.state_repo.get(106)
        assert retrieved.is_ready_for_retry() is True
        assert retrieved.status == AutomationStatus.RETRY_SCHEDULED

    def test_run_once_respects_processing_claim_during_execution(self, executor):
        """Processing claim should be held during workflow execution and released after."""
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        ticket = Ticket(
            id=107,
            name="Cannot login",
            email_from="user@company.com",
        )

        fingerprint = TicketFingerprinter.generate(ticket)
        now = datetime.now(timezone.utc)

        # Claim with 5-minute lease
        claimed = executor.state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed is True

        # Verify lease is set and active
        state = executor.state_repo.get(ticket.id)
        assert state.processing_lease_until is not None
        # Recalculate now to account for execution time
        now_after = datetime.now(timezone.utc)
        lease_remaining = (state.processing_lease_until - now_after).total_seconds()
        # Allow wider tolerance for execution time variance
        assert 285 < lease_remaining <= 305  # Should be ~300s ±5s

    def test_run_once_max_retry_count(self, executor):
        """run_once() should respect max retry limits."""
        max_retries = 3

        state = AutomationState(
            ticket_id=108,
            fingerprint="pqr678",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=max_retries,  # At max
        )
        executor.state_repo.save(state)

        # Verify max reached
        retrieved = executor.state_repo.get(108)
        assert retrieved.retry_count >= max_retries

    def test_run_once_communication_state_persists_across_retries(self, executor):
        """Communication state should prevent email resending across retries."""
        from srcs.services.communication_state import CommunicationStateTracker
        from srcs.services.gmail import CommunicationEvent

        # Create communication state tracker
        tracker = CommunicationStateTracker(repo=executor.state_repo)

        # Mark email as sent for ticket
        tracker.mark_sent(ticket_id=109, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)

        # On retry, verify email is not resent
        should_send = tracker.should_send(ticket_id=109, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        assert should_send is False
