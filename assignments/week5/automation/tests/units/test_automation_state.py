"""Unit tests for AutomationState model."""

import pytest
from datetime import datetime, timedelta, timezone
from srcs.models import AutomationState, AutomationStatus


class TestAutomationStateCreation:
    """Test AutomationState model creation and validation."""

    def test_create_automation_state_minimal(self):
        """Should create state with required fields only."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )

        assert state.ticket_id == 1
        assert state.fingerprint == "abc123"
        assert state.status == AutomationStatus.PENDING
        assert state.retry_count == 0
        assert state.reactivation_completed is False

    def test_create_automation_state_with_all_fields(self):
        """Should create state with all fields."""
        now = datetime.now(timezone.utc)
        retry_time = now + timedelta(hours=1)

        state = AutomationState(
            ticket_id=2,
            fingerprint="def456",
            status=AutomationStatus.RETRY_SCHEDULED,
            last_decision="approve_reactivation",
            last_reason="Employee active, deactivated due to inactivity",
            created_at=now,
            updated_at=now,
            last_checked_at=now,
            retry_count=1,
            next_retry_at=retry_time,
            last_error="Odoo communication timeout",
            reactivation_completed=True,
            odoo_note_completed=False,
        )

        assert state.ticket_id == 2
        assert state.status == AutomationStatus.RETRY_SCHEDULED
        assert state.last_decision == "approve_reactivation"
        assert state.retry_count == 1
        assert state.reactivation_completed is True
        assert state.odoo_note_completed is False

    def test_validation_invalid_ticket_id(self):
        """Should reject invalid ticket ID."""
        with pytest.raises(ValueError):
            AutomationState(
                ticket_id=0,
                fingerprint="abc123",
                status=AutomationStatus.PENDING,
            )

    def test_validation_empty_fingerprint(self):
        """Should reject empty fingerprint."""
        with pytest.raises(ValueError):
            AutomationState(
                ticket_id=1,
                fingerprint="",
                status=AutomationStatus.PENDING,
            )


class TestAutomationStatusEnum:
    """Test AutomationStatus enumeration."""

    def test_all_statuses_exist(self):
        """Should have all required statuses."""
        assert AutomationStatus.PENDING.value == "pending"
        assert AutomationStatus.PROCESSING.value == "processing"
        assert AutomationStatus.COMPLETED.value == "completed"
        assert AutomationStatus.MANUAL_REVIEW.value == "manual_review"
        assert AutomationStatus.SKIPPED.value == "skipped"
        assert AutomationStatus.RETRY_SCHEDULED.value == "retry_scheduled"
        assert AutomationStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Should create status from string value."""
        status = AutomationStatus("pending")
        assert status == AutomationStatus.PENDING


class TestAutomationStateRetryLogic:
    """Test retry readiness check."""

    def test_not_ready_when_not_retry_status(self):
        """Should not be ready if status is not RETRY_SCHEDULED."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )

        assert state.is_ready_for_retry() is False

    def test_ready_when_retry_with_no_next_time(self):
        """Should be ready for retry if status is RETRY_SCHEDULED and no retry time set."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=None,
        )

        assert state.is_ready_for_retry() is True

    def test_not_ready_when_retry_time_in_future(self):
        """Should not be ready if retry time is in the future."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=future_time,
        )

        assert state.is_ready_for_retry() is False

    def test_ready_when_retry_time_in_past(self):
        """Should be ready if retry time has passed."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=past_time,
        )

        assert state.is_ready_for_retry() is True


class TestAutomationStateSerialization:
    """Test serialization and deserialization."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        now = datetime.now(timezone.utc)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.COMPLETED,
            last_decision="approve_reactivation",
            last_reason="Test reason",
            created_at=now,
            updated_at=now,
            retry_count=0,
            reactivation_completed=True,
        )

        data = state.to_dict()

        assert data["ticket_id"] == 1
        assert data["fingerprint"] == "abc123"
        assert data["status"] == "completed"
        assert data["last_decision"] == "approve_reactivation"
        assert data["retry_count"] == 0
        assert data["reactivation_completed"] is True
        assert isinstance(data["created_at"], str)

    def test_from_dict(self):
        """Should create from dictionary."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "ticket_id": 2,
            "fingerprint": "def456",
            "status": "pending",
            "last_decision": None,
            "last_reason": None,
            "created_at": now,
            "updated_at": now,
            "last_checked_at": None,
            "retry_count": 0,
            "next_retry_at": None,
            "last_error": None,
            "reactivation_completed": False,
            "odoo_note_completed": False,
            "customer_response_completed": False,
            "stage_update_completed": False,
        }

        state = AutomationState.from_dict(data)

        assert state.ticket_id == 2
        assert state.fingerprint == "def456"
        assert state.status == AutomationStatus.PENDING
        assert state.retry_count == 0

    def test_roundtrip_serialization(self):
        """Should preserve data through to_dict/from_dict roundtrip."""
        now = datetime.now(timezone.utc)
        original = AutomationState(
            ticket_id=3,
            fingerprint="ghi789",
            status=AutomationStatus.MANUAL_REVIEW,
            last_decision="manual_review",
            last_reason="Employee terminated",
            created_at=now,
            updated_at=now,
            retry_count=2,
            last_error="Some error",
            reactivation_completed=False,
            odoo_note_completed=True,
        )

        data = original.to_dict()
        restored = AutomationState.from_dict(data)

        assert restored.ticket_id == original.ticket_id
        assert restored.fingerprint == original.fingerprint
        assert restored.status == original.status
        assert restored.last_decision == original.last_decision
        assert restored.retry_count == original.retry_count
        assert restored.reactivation_completed == original.reactivation_completed
        assert restored.odoo_note_completed == original.odoo_note_completed


class TestAutomationStateTimestamps:
    """Test timestamp handling."""

    def test_created_at_defaults_to_now(self):
        """Should default created_at to current timezone.utc time."""
        before = datetime.now(timezone.utc)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )
        after = datetime.now(timezone.utc)

        assert before <= state.created_at <= after

    def test_updated_at_defaults_to_now(self):
        """Should default updated_at to current timezone.utc time."""
        before = datetime.now(timezone.utc)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )
        after = datetime.now(timezone.utc)

        assert before <= state.updated_at <= after

    def test_timestamps_are_utc(self):
        """Timestamps should be in timezone.utc."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )

        # datetime.now(timezone.utc) returns timezone-aware datetime in timezone.utc
        assert state.created_at.tzinfo is not None
        assert state.updated_at.tzinfo is not None
        assert state.created_at.tzinfo == timezone.utc
        assert state.updated_at.tzinfo == timezone.utc


class TestAutomationStateSideEffectTracking:
    """Test side effect completion flags."""

    def test_all_side_effects_default_to_false(self):
        """Should track all side effects as incomplete by default."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PENDING,
        )

        assert state.reactivation_completed is False
        assert state.odoo_note_completed is False
        assert state.customer_response_completed is False
        assert state.stage_update_completed is False

    def test_partial_completion_tracking(self):
        """Should track which side effects have completed."""
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,
            odoo_note_completed=True,
            customer_response_completed=False,
            stage_update_completed=False,
        )

        assert state.reactivation_completed is True
        assert state.odoo_note_completed is True
        assert state.customer_response_completed is False
        assert state.stage_update_completed is False
