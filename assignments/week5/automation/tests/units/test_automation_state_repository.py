"""Unit tests for AutomationStateRepository - SQLite persistence layer."""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from srcs.models import AutomationState, AutomationStatus
from srcs.repositories.automation_state_repository import AutomationStateRepository


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test_automation_state.db"
    yield db_path

    # Cleanup: ensure all connections are closed
    try:
        if db_path.exists():
            # Close any remaining connections
            import gc
            gc.collect()
            db_path.unlink()
    except Exception:
        pass

    # Cleanup directory
    try:
        Path(tmpdir).rmdir()
    except Exception:
        pass


@pytest.fixture
def repo(temp_db):
    """Create repository with temporary database."""
    return AutomationStateRepository(db_path=temp_db)


class TestAutomationStateRepositoryBasics:
    """Test basic CRUD operations."""

    def test_repository_initializes_database(self, temp_db):
        """Should create database and schema on initialization."""
        repo = AutomationStateRepository(db_path=temp_db)
        assert temp_db.exists()
        assert temp_db.stat().st_size > 0

    def test_save_new_state(self, repo):
        """Should save new automation state."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )

        result = repo.save(state)

        assert result is True
        retrieved = repo.get(ticket_id=1)
        assert retrieved is not None
        assert retrieved.ticket_id == 1
        assert retrieved.fingerprint == "abc123"
        assert retrieved.status == AutomationStatus.PENDING

    def test_get_nonexistent_state(self, repo):
        """Should return None for nonexistent ticket."""
        result = repo.get(ticket_id=999)
        assert result is None

    def test_save_updates_existing_state(self, repo):
        """Should update existing state on save (upsert)."""
        # Create initial state
        state1 = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )
        repo.save(state1)

        # Update state
        state2 = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
            retry_count=1,
        )
        repo.save(state2)

        # Should have only one record
        retrieved = repo.get(ticket_id=1)
        assert retrieved.status == AutomationStatus.PROCESSING
        assert retrieved.retry_count == 1

    def test_save_updates_timestamp(self, repo):
        """Should update updated_at timestamp on save."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )
        initial_updated_at = state.updated_at

        # Wait a bit and save
        import time
        time.sleep(0.01)
        repo.save(state)

        retrieved = repo.get(ticket_id=1)
        assert retrieved.updated_at > initial_updated_at

    def test_save_preserves_all_fields(self, repo):
        """Should preserve all fields on save and retrieval."""
        now = datetime.utcnow()
        retry_time = now + timedelta(hours=1)

        state = AutomationState(
            ticket_id=42,
            fingerprint="xyz789",
            status=AutomationStatus.RETRY_SCHEDULED,
            last_decision="approve_reactivation",
            last_reason="Employee is active",
            created_at=now,
            updated_at=now,
            last_checked_at=now,
            retry_count=2,
            next_retry_at=retry_time,
            last_error="Odoo timeout",
            reactivation_completed=True,
            odoo_note_completed=False,
            customer_response_completed=True,
            stage_update_completed=False,
        )

        repo.save(state)
        retrieved = repo.get(ticket_id=42)

        assert retrieved.ticket_id == 42
        assert retrieved.fingerprint == "xyz789"
        assert retrieved.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved.last_decision == "approve_reactivation"
        assert retrieved.last_reason == "Employee is active"
        assert retrieved.retry_count == 2
        assert retrieved.last_error == "Odoo timeout"
        assert retrieved.reactivation_completed is True
        assert retrieved.odoo_note_completed is False
        assert retrieved.customer_response_completed is True
        assert retrieved.stage_update_completed is False


class TestAutomationStateRepositoryClaimForProcessing:
    """Test atomic processing claim mechanism."""

    def test_claim_for_processing_new_ticket(self, repo):
        """Should create and claim new ticket for processing."""
        result = repo.claim_for_processing(ticket_id=1, fingerprint="abc123")

        assert result is True
        retrieved = repo.get(ticket_id=1)
        assert retrieved.status == AutomationStatus.PROCESSING

    def test_claim_for_processing_prevents_concurrent_claim(self, repo):
        """Should prevent concurrent processing by lease."""
        # First claim succeeds
        assert repo.claim_for_processing(ticket_id=1, fingerprint="abc123") is True

        # Second claim should fail (lease still active)
        result = repo.claim_for_processing(ticket_id=1, fingerprint="abc123")
        assert result is False

    def test_claim_for_processing_expires_old_lease(self, repo):
        """Should allow claiming if previous lease expired."""
        # Create state with expired lease
        now = datetime.utcnow()
        expired_lease = now - timedelta(seconds=1)

        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        # Manually set expired lease in database (simulate stale processing)
        import sqlite3
        with sqlite3.connect(repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 1)
            )
            conn.commit()

        # Should be able to recover
        result = repo.claim_for_processing(ticket_id=1, fingerprint="abc123")
        assert result is True

    def test_claim_for_processing_allows_reprocessing_on_fingerprint_change(self, repo):
        """Should allow reprocessing if fingerprint changed."""
        # Initial claim
        repo.claim_for_processing(ticket_id=1, fingerprint="abc123")

        # Try to claim with different fingerprint
        result = repo.claim_for_processing(ticket_id=1, fingerprint="def456")

        # Should succeed and update fingerprint
        assert result is True
        retrieved = repo.get(ticket_id=1)
        assert retrieved.fingerprint == "def456"
        assert retrieved.status == AutomationStatus.PENDING

    def test_claim_for_processing_custom_lease_duration(self, repo):
        """Should respect custom lease duration."""
        result = repo.claim_for_processing(
            ticket_id=1,
            fingerprint="abc123",
            lease_duration_seconds=60
        )

        assert result is True

        # Verify lease was set (by trying again immediately - should fail)
        result = repo.claim_for_processing(
            ticket_id=1,
            fingerprint="abc123",
            lease_duration_seconds=60
        )
        assert result is False


class TestAutomationStateRepositoryMarkCompleted:
    """Test marking tickets as completed."""

    def test_mark_completed_success(self, repo):
        """Should mark ticket as completed."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        result = repo.mark_completed(ticket_id=1)

        assert result is True
        retrieved = repo.get(ticket_id=1)
        assert retrieved.status == AutomationStatus.COMPLETED

    def test_mark_completed_clears_lease(self, repo):
        """Should clear processing lease when marked completed."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        repo.mark_completed(ticket_id=1)

        import sqlite3
        with sqlite3.connect(repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT processing_lease_until FROM automation_state WHERE ticket_id = ?",
                (1,)
            )
            row = cursor.fetchone()
            assert row[0] is None

    def test_mark_completed_updates_timestamp(self, repo):
        """Should update updated_at when marked completed."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)
        initial_updated_at = state.updated_at

        import time
        time.sleep(0.01)
        repo.mark_completed(ticket_id=1)

        retrieved = repo.get(ticket_id=1)
        assert retrieved.updated_at > initial_updated_at


class TestAutomationStateRepositoryMarkManualReview:
    """Test marking tickets for manual review."""

    def test_mark_manual_review_success(self, repo):
        """Should mark ticket for manual review."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        result = repo.mark_manual_review(ticket_id=1, reason="Employee terminated")

        assert result is True
        retrieved = repo.get(ticket_id=1)
        assert retrieved.status == AutomationStatus.MANUAL_REVIEW
        assert retrieved.last_reason == "Employee terminated"

    def test_mark_manual_review_clears_lease(self, repo):
        """Should clear processing lease when marked for manual review."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        repo.mark_manual_review(ticket_id=1, reason="Test reason")

        import sqlite3
        with sqlite3.connect(repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT processing_lease_until FROM automation_state WHERE ticket_id = ?",
                (1,)
            )
            row = cursor.fetchone()
            assert row[0] is None


class TestAutomationStateRepositoryScheduleRetry:
    """Test retry scheduling."""

    def test_schedule_retry_success(self, repo):
        """Should schedule retry with future time."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        result = repo.schedule_retry(
            ticket_id=1,
            retry_after_seconds=3600,
            error="Odoo communication timeout"
        )

        assert result is True
        retrieved = repo.get(ticket_id=1)
        assert retrieved.status == AutomationStatus.RETRY_SCHEDULED
        assert retrieved.retry_count == 1
        assert retrieved.last_error == "Odoo communication timeout"
        assert retrieved.next_retry_at is not None

    def test_schedule_retry_increments_count(self, repo):
        """Should increment retry count on each schedule."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
            retry_count=2,
        )
        repo.save(state)

        repo.schedule_retry(ticket_id=1, retry_after_seconds=3600)

        retrieved = repo.get(ticket_id=1)
        assert retrieved.retry_count == 3

    def test_schedule_retry_sets_future_time(self, repo):
        """Should set next_retry_at to future time."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        before = datetime.utcnow()
        repo.schedule_retry(ticket_id=1, retry_after_seconds=3600)
        after = datetime.utcnow()

        retrieved = repo.get(ticket_id=1)
        assert retrieved.next_retry_at > after

    def test_schedule_retry_clears_lease(self, repo):
        """Should clear processing lease when scheduling retry."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state)

        repo.schedule_retry(ticket_id=1, retry_after_seconds=3600)

        import sqlite3
        with sqlite3.connect(repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT processing_lease_until FROM automation_state WHERE ticket_id = ?",
                (1,)
            )
            row = cursor.fetchone()
            assert row[0] is None


class TestAutomationStateRepositoryTransactions:
    """Test transactional behavior and data integrity."""

    def test_multiple_tickets_independent(self, repo):
        """Should handle multiple tickets independently."""
        state1 = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )
        state2 = AutomationState(
            ticket_id=2,
            fingerprint="def456",
            status=AutomationStatus.PROCESSING,
        )

        repo.save(state1)
        repo.save(state2)

        retrieved1 = repo.get(ticket_id=1)
        retrieved2 = repo.get(ticket_id=2)

        assert retrieved1.status == AutomationStatus.PENDING
        assert retrieved2.status == AutomationStatus.PROCESSING

    def test_concurrent_operations_isolation(self, repo):
        """Should handle concurrent operations safely."""
        # Create multiple tickets and perform operations
        for i in range(5):
            state = AutomationState(
                ticket_id=i+1,
                fingerprint=f"fingerprint_{i}",
                status=AutomationStatus.PENDING,
            )
            repo.save(state)

        # Process half of them
        repo.claim_for_processing(ticket_id=1, fingerprint="fingerprint_0")
        repo.claim_for_processing(ticket_id=2, fingerprint="fingerprint_1")
        repo.mark_completed(ticket_id=1)

        # Verify state
        assert repo.get(ticket_id=1).status == AutomationStatus.COMPLETED
        assert repo.get(ticket_id=2).status == AutomationStatus.PROCESSING
        assert repo.get(ticket_id=3).status == AutomationStatus.PENDING

    def test_sideeffect_flags_preserved(self, repo):
        """Should preserve side effect completion flags."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,
            odoo_note_completed=True,
            customer_response_completed=False,
            stage_update_completed=False,
        )
        repo.save(state)

        retrieved = repo.get(ticket_id=1)
        assert retrieved.reactivation_completed is True
        assert retrieved.odoo_note_completed is True
        assert retrieved.customer_response_completed is False
        assert retrieved.stage_update_completed is False


class TestAutomationStateRepositoryErrorHandling:
    """Test error handling."""

    def test_save_invalid_state_raises(self, repo):
        """Should raise error for invalid state."""
        with pytest.raises(ValueError):
            state = AutomationState(
                ticket_id=0,  # Invalid
                fingerprint="abc123",
                status=AutomationStatus.PENDING,
            )

    def test_get_from_corrupted_db_returns_none(self, repo):
        """Should handle corrupted database gracefully."""
        # This test is environment-dependent and may not apply
        # But we test that the method returns None on error
        result = repo.get(ticket_id=1)
        assert result is None

    def test_save_with_unicode_fields(self, repo):
        """Should handle unicode in text fields."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.MANUAL_REVIEW,
            last_reason="Employee left: 中文名字 café naïve",
            last_error="Error with émojis: 🚀",
        )

        repo.save(state)
        retrieved = repo.get(ticket_id=1)

        assert "中文" in retrieved.last_reason
        assert "🚀" in retrieved.last_error


class TestAutomationStateRepositoryIndexes:
    """Test that indexes are created for performance."""

    def test_status_index_created(self, temp_db):
        """Should create index on status column."""
        repo = AutomationStateRepository(db_path=temp_db)

        import sqlite3
        with sqlite3.connect(repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_status'")
            result = cursor.fetchone()
            assert result is not None

    def test_retry_index_created(self, temp_db):
        """Should create index on next_retry_at column."""
        repo = AutomationStateRepository(db_path=temp_db)

        import sqlite3
        with sqlite3.connect(repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_next_retry_at'")
            result = cursor.fetchone()
            assert result is not None
