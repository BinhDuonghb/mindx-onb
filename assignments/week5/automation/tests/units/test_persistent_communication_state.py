"""Test persistent communication state - RED phase.

Verify that communication events persist to SQLite across process restarts
and prevent duplicate sends even after application restart.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from srcs.services.communication_state import CommunicationStateTracker
from srcs.services.gmail import CommunicationEvent
from srcs.repositories.automation_state_repository import AutomationStateRepository


class TestPersistentCommunicationEvents:
    """Test communication events persist to SQLite."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_save_event_persists_to_database(self, temp_db):
        """Mark sent event should persist to SQLite."""
        repo = AutomationStateRepository(db_path=temp_db)

        # Mark event as sent
        repo.mark_communication_sent(
            ticket_id=1,
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        )

        # Verify it was saved
        assert repo.has_communication_sent(
            ticket_id=1,
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        ) is True

    def test_load_events_on_repository_init(self, temp_db):
        """Events saved in first repo should be found in second repo."""
        # First repo: save event
        repo1 = AutomationStateRepository(db_path=temp_db)
        repo1.mark_communication_sent(
            ticket_id=1,
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        )

        # Second repo: load from same database
        repo2 = AutomationStateRepository(db_path=temp_db)

        # Should find the persisted event
        assert repo2.has_communication_sent(
            ticket_id=1,
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        ) is True

    def test_tracker_loads_persisted_events(self, temp_db):
        """CommunicationStateTracker should load persisted events on init."""
        # First tracker: mark event as sent via repo
        repo1 = AutomationStateRepository(db_path=temp_db)
        repo1.mark_communication_sent(
            ticket_id=1,
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        )

        # Second tracker: should load from repo
        repo2 = AutomationStateRepository(db_path=temp_db)
        tracker2 = CommunicationStateTracker(repo=repo2)

        # Should not send duplicate
        assert tracker2.should_send(
            ticket_id=1,
            event=CommunicationEvent.REACTIVATION_SUCCESSFUL
        ) is False

    def test_multiple_events_per_ticket_persist(self, temp_db):
        """Multiple events for same ticket should persist independently."""
        repo1 = AutomationStateRepository(db_path=temp_db)

        # Mark multiple events
        repo1.mark_communication_sent(ticket_id=1, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        repo1.mark_communication_sent(ticket_id=1, event=CommunicationEvent.FOLLOW_UP_REMINDER)

        # New repo loads both
        repo2 = AutomationStateRepository(db_path=temp_db)

        assert repo2.has_communication_sent(ticket_id=1, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        assert repo2.has_communication_sent(ticket_id=1, event=CommunicationEvent.FOLLOW_UP_REMINDER)
        # But other events should not be marked
        assert not repo2.has_communication_sent(ticket_id=1, event=CommunicationEvent.MANUAL_REVIEW_REQUIRED)

    def test_multiple_tickets_independent_state(self, temp_db):
        """Different tickets should have independent communication state."""
        repo1 = AutomationStateRepository(db_path=temp_db)

        # Ticket 1: mark resolution
        repo1.mark_communication_sent(ticket_id=1, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        # Ticket 2: mark manual review
        repo1.mark_communication_sent(ticket_id=2, event=CommunicationEvent.MANUAL_REVIEW_REQUIRED)

        # New repo loads both
        repo2 = AutomationStateRepository(db_path=temp_db)

        # Ticket 1 state
        assert repo2.has_communication_sent(ticket_id=1, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        assert not repo2.has_communication_sent(ticket_id=1, event=CommunicationEvent.MANUAL_REVIEW_REQUIRED)

        # Ticket 2 state
        assert not repo2.has_communication_sent(ticket_id=2, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        assert repo2.has_communication_sent(ticket_id=2, event=CommunicationEvent.MANUAL_REVIEW_REQUIRED)

    def test_prevent_duplicate_email_after_restart(self, temp_db):
        """Should prevent duplicate emails even after process restart."""
        # First "run": mark email as sent
        repo1 = AutomationStateRepository(db_path=temp_db)
        repo1.mark_communication_sent(ticket_id=100, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)

        # Simulate process restart: new repo and tracker
        repo2 = AutomationStateRepository(db_path=temp_db)
        tracker2 = CommunicationStateTracker(repo=repo2)

        # Should NOT send duplicate
        assert not tracker2.should_send(ticket_id=100, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)

        # But can send other events
        assert tracker2.should_send(ticket_id=100, event=CommunicationEvent.FOLLOW_UP_REMINDER)

    def test_backward_compatibility_no_repo_provided(self):
        """Should work as in-memory if no repo provided (backwards compatibility)."""
        tracker = CommunicationStateTracker(repo=None)

        # Should work like before (in-memory only)
        tracker.mark_sent(ticket_id=1, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)
        assert not tracker.should_send(ticket_id=1, event=CommunicationEvent.REACTIVATION_SUCCESSFUL)

    def test_confirmation_persists_across_restart(self, temp_db):
        """Customer confirmation should persist after restart."""
        confirmed_time = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)

        # First repo: mark confirmed
        repo1 = AutomationStateRepository(db_path=temp_db)
        repo1.mark_communication_confirmed(ticket_id=1, confirmed_at=confirmed_time)

        # Second repo: load from database
        repo2 = AutomationStateRepository(db_path=temp_db)
        tracker2 = CommunicationStateTracker(repo=repo2)

        # Should remember confirmation
        assert tracker2.is_confirmed(ticket_id=1)
        assert tracker2.get_confirmed_at(ticket_id=1) == confirmed_time
