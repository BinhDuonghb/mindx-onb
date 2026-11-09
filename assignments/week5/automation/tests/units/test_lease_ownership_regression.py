"""Regression tests for lease ownership — atomic SQL validation.

Tests that stale workers cannot modify active leases, and that runners pass
ownership tokens through the entire workflow.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

from srcs.models import AutomationState, AutomationStatus, Ticket
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter


class TestLeaseOwnershipRegression:
    """Regression tests for atomic SQL ownership validation."""

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

    def test_stale_worker_cannot_save_completed_state(self, temp_db):
        """Stale worker cannot save COMPLETED state over owned ticket."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=3001, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims and processes
        token_a = repo.claim_for_processing(ticket_id=3001, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire Worker A's lease and Worker B claims
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 3001)
            )
            conn.commit()

        token_b = repo.claim_for_processing(ticket_id=3001, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None
        assert token_b != token_a

        # Worker A (stale) tries to save COMPLETED state with old token
        completed_state = AutomationState(
            ticket_id=3001,
            fingerprint=fp,
            status=AutomationStatus.COMPLETED,
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True
        )

        # SHOULD REJECT: stale worker with wrong token
        result = repo.save(completed_state, owner_token=token_a)
        assert result is False, "Stale worker save of COMPLETED state should be rejected"

        # Verify Worker B still owns the ticket and state is unchanged
        state_final = repo.get(3001)
        assert state_final.lease_owner_token == token_b
        assert state_final.status == AutomationStatus.PROCESSING
        assert state_final.reactivation_completed is False

    def test_save_without_token_rejected_for_owned_ticket(self, temp_db):
        """save() without token must be rejected if record has active lease."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=3002, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker claims ticket (creates active lease)
        token = repo.claim_for_processing(ticket_id=3002, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        state_before = repo.get(3002)
        assert state_before.lease_owner_token == token
        assert state_before.processing_lease_until is not None

        # Try to save without any token (no owner_token parameter)
        state_update = AutomationState(
            ticket_id=3002,
            fingerprint=fp,
            status=AutomationStatus.COMPLETED,
            reactivation_completed=True
        )

        # SHOULD REJECT: no token provided but record has active lease
        result = repo.save(state_update, owner_token=None)
        assert result is False, "save() without token must be rejected for owned ticket"

        # Verify state unchanged
        state_after = repo.get(3002)
        assert state_after.lease_owner_token == token
        assert state_after.status == AutomationStatus.PROCESSING
        assert state_after.reactivation_completed is False

    def test_valid_owner_can_save_completed_state(self, temp_db):
        """Valid owner CAN save COMPLETED state with correct token."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=3003, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker claims ticket
        token = repo.claim_for_processing(ticket_id=3003, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        # Valid owner saves COMPLETED state with correct token
        completed_state = AutomationState(
            ticket_id=3003,
            fingerprint=fp,
            status=AutomationStatus.COMPLETED,
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True
        )

        # SHOULD SUCCEED: correct token with active lease
        result = repo.save(completed_state, owner_token=token)
        assert result is True, "Valid owner save should succeed"

        # Verify state was updated
        state_final = repo.get(3003)
        assert state_final.status == AutomationStatus.COMPLETED
        assert state_final.reactivation_completed is True
        assert state_final.odoo_note_completed is True
        assert state_final.stage_update_completed is True

    def test_runner_schedules_retry_with_owner_token(self, temp_db):
        """Runner passes owner_token to schedule_retry() and sets next_retry_at."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=3004, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Runner claims ticket
        token = repo.claim_for_processing(ticket_id=3004, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        state_before = repo.get(3004)
        assert state_before.status == AutomationStatus.PROCESSING
        assert state_before.next_retry_at is None

        # Runner schedules retry with owner token (as per Fix 2)
        retry_result = repo.schedule_retry(
            ticket_id=3004,
            retry_after_seconds=3600,
            error="Test error",
            owner_token=token  # Fix 2: Pass owner token
        )

        # SHOULD SUCCEED: correct token allows retry scheduling
        assert retry_result is True, "schedule_retry with valid token should succeed"

        # Verify state transitioned and next_retry_at is set
        state_final = repo.get(3004)
        assert state_final.status == AutomationStatus.RETRY_SCHEDULED
        assert state_final.next_retry_at is not None
        # Owner should be released on successful retry
        assert state_final.lease_owner_token is None
        assert state_final.processing_lease_until is None

    def test_missing_token_cannot_release_active_lease(self, temp_db):
        """schedule_retry() without token must reject active lease."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=3005, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker claims
        token = repo.claim_for_processing(ticket_id=3005, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        state_before = repo.get(3005)
        lease_before = state_before.processing_lease_until

        # Try to schedule retry without token
        retry_result = repo.schedule_retry(
            ticket_id=3005,
            retry_after_seconds=3600,
            error="Test error",
            owner_token=None  # No token provided
        )

        # SHOULD REJECT: no token but active lease exists
        assert retry_result is False, "schedule_retry without token must reject active lease"

        # Verify state unchanged
        state_after = repo.get(3005)
        assert state_after.status == AutomationStatus.PROCESSING
        assert state_after.processing_lease_until == lease_before
        assert state_after.lease_owner_token == token
