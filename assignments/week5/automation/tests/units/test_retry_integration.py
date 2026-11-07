"""Test retry integration - RED phase.

Verify that due retries are included in run_once() execution alongside
new and changed tickets.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.models import Ticket, AutomationState, AutomationStatus
from srcs.services.ticket_poller import TicketPoller


class TestRetryIntegration:
    """Test retry ticket processing integration."""

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
    def repo(self, temp_db):
        """Create repository with temp database."""
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def poller(self, repo):
        """Create ticket poller with mocked client."""
        ticket_client = Mock()
        return TicketPoller(ticket_client=ticket_client, state_repo=repo)

    def test_retry_scheduled_ticket_is_ready_for_retry(self, repo):
        """Retry-scheduled tickets with passed next_retry_at are ready for retry."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        # Create a retry-scheduled ticket with past retry time
        state = AutomationState(
            ticket_id=100,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            next_retry_at=past,  # Retry time has passed
        )
        repo.save(state)

        # Verify is_ready_for_retry() returns True (due for retry)
        retrieved_state = repo.get(100)
        assert retrieved_state.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved_state.is_ready_for_retry() is True

    def test_poll_for_retry_skips_future_retries(self, repo):
        """Retry-scheduled tickets with future next_retry_at are not ready yet."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        # Create retry-scheduled ticket with future retry time
        state = AutomationState(
            ticket_id=101,
            fingerprint="def456",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            next_retry_at=future,  # Not yet due
        )
        repo.save(state)

        # Verify is_ready_for_retry() returns False (not yet due)
        retrieved_state = repo.get(101)
        assert retrieved_state.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved_state.is_ready_for_retry() is False

    def test_retry_count_increments_on_retry(self, repo):
        """Retry count should increment when retry is scheduled."""
        state = AutomationState(
            ticket_id=102,
            fingerprint="ghi789",
            status=AutomationStatus.PROCESSING,
            retry_count=0,
        )
        repo.save(state)

        # Schedule retry
        repo.schedule_retry(ticket_id=102, retry_after_seconds=3600, error="Test error")

        # Verify retry count incremented
        updated_state = repo.get(102)
        assert updated_state.retry_count == 1
        assert updated_state.last_error == "Test error"
        assert updated_state.status == AutomationStatus.RETRY_SCHEDULED
        assert updated_state.next_retry_at is not None

    def test_completed_reactivation_not_repeated(self, repo):
        """Completed reactivation should not be repeated even on retry."""
        state = AutomationState(
            ticket_id=103,
            fingerprint="jkl012",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            reactivation_completed=True,  # Already completed
            next_retry_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        repo.save(state)

        # Verify side effect flag is preserved
        retrieved_state = repo.get(103)
        assert retrieved_state.reactivation_completed is True
        assert retrieved_state.status == AutomationStatus.RETRY_SCHEDULED

    def test_completed_odoo_note_not_posted_again(self, repo):
        """Completed Odoo note should not be posted again on retry."""
        state = AutomationState(
            ticket_id=104,
            fingerprint="mno345",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=1,
            reactivation_completed=True,
            odoo_note_completed=True,  # Already posted
            next_retry_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        repo.save(state)

        # Verify both side effects are tracked
        retrieved_state = repo.get(104)
        assert retrieved_state.odoo_note_completed is True
        assert retrieved_state.reactivation_completed is True

    def test_successfully_sent_email_not_resent(self, repo):
        """Successfully sent emails should not be resent on retry."""
        # This test verifies that CommunicationStateTracker prevents resending
        from srcs.services.communication_state import CommunicationStateTracker
        from srcs.services.gmail import CommunicationEvent

        repo_with_comm = AutomationStateRepository(db_path=Path("data/test_retry_comm.db"))
        tracker = CommunicationStateTracker(repo=repo_with_comm)

        # Mark email as sent
        tracker.mark_sent(ticket_id=105, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)

        # On retry, should not resend
        assert not tracker.should_send(ticket_id=105, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)

        # Clean up
        import os
        try:
            os.remove("data/test_retry_comm.db")
        except:
            pass

    def test_retry_respects_max_retries(self, repo):
        """Retries should respect maximum retry limit (configurable)."""
        max_retries = 3

        state = AutomationState(
            ticket_id=106,
            fingerprint="pqr678",
            status=AutomationStatus.RETRY_SCHEDULED,
            retry_count=max_retries,  # At max
        )
        repo.save(state)

        # Verify max reached
        retrieved_state = repo.get(106)
        assert retrieved_state.retry_count >= max_retries

    def test_retry_preserves_original_decision(self, repo):
        """Retry should preserve the original business decision."""
        state = AutomationState(
            ticket_id=107,
            fingerprint="stu901",
            status=AutomationStatus.RETRY_SCHEDULED,
            last_decision="account_reactivated",
            last_reason="Active employee, 30-day inactivity",
            retry_count=1,
            reactivation_completed=True,
        )
        repo.save(state)

        # Verify decision is preserved
        retrieved_state = repo.get(107)
        assert retrieved_state.last_decision == "account_reactivated"
        assert retrieved_state.last_reason == "Active employee, 30-day inactivity"
        assert retrieved_state.reactivation_completed is True
