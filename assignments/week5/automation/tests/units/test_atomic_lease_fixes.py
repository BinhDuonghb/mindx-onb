"""Regression tests for atomic lease fixes.

Tests concurrent claim atomicity, token expiration protection, and lease release.
"""

import pytest
import tempfile
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

from srcs.models import AutomationState, AutomationStatus, Ticket
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter


class TestAtomicLeaseFixes:
    """Tests for atomic claim, expiration protection, and lease release."""

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

    def test_concurrent_expired_lease_only_one_worker_claims(self, temp_db):
        """Only one worker can claim when lease is expired (atomicity test)."""
        # Setup: Worker A claims, then lease expires
        repo_a = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4001, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        token_a = repo_a.claim_for_processing(ticket_id=4001, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Manually expire the lease
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 4001)
            )
            conn.commit()

        # Now: Two workers race to claim the same expired ticket
        claimed_tokens = []
        lock = threading.Lock()

        def worker_claim(worker_id):
            repo = AutomationStateRepository(db_path=temp_db)
            token = repo.claim_for_processing(ticket_id=4001, fingerprint=fp, lease_duration_seconds=300)
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

        # Verify: Only one worker succeeded
        assert len(claimed_tokens) == 1, f"Expected 1 successful claim, got {len(claimed_tokens)}"
        winner_id, winner_token = claimed_tokens[0]

        # Verify database state
        final_state = repo_a.get(4001)
        assert final_state.lease_owner_token == winner_token
        assert final_state.processing_lease_until is not None
        now_check = datetime.now(timezone.utc)
        # Handle both string and datetime types
        if isinstance(final_state.processing_lease_until, str):
            lease_until = datetime.fromisoformat(final_state.processing_lease_until)
        else:
            lease_until = final_state.processing_lease_until
        assert lease_until > now_check  # New lease is in the future

    def test_concurrent_fingerprint_change_only_one_worker_claims(self, temp_db):
        """Only one worker claims when fingerprint changes and lease expires."""
        repo_a = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4002, name="Test", email_from="test@company.com")
        fp1 = TicketFingerprinter.generate(ticket)

        token_a = repo_a.claim_for_processing(ticket_id=4002, fingerprint=fp1, lease_duration_seconds=300)
        assert token_a is not None

        # Expire lease
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 4002)
            )
            conn.commit()

        # Simulate ticket change: different fingerprint
        ticket.name = "Test (Updated)"
        fp2 = TicketFingerprinter.generate(ticket)
        assert fp2 != fp1

        # Two workers race with different fingerprints
        claimed_tokens = []
        lock = threading.Lock()

        def worker_claim(worker_id, fingerprint):
            repo = AutomationStateRepository(db_path=temp_db)
            token = repo.claim_for_processing(ticket_id=4002, fingerprint=fingerprint, lease_duration_seconds=300)
            if token is not None:
                with lock:
                    claimed_tokens.append((worker_id, token, fingerprint))

        threads = [
            threading.Thread(target=worker_claim, args=(1, fp1)),
            threading.Thread(target=worker_claim, args=(2, fp2))
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed
        assert len(claimed_tokens) == 1, f"Expected 1 successful claim, got {len(claimed_tokens)}"
        winner_id, winner_token, winner_fp = claimed_tokens[0]

        final_state = repo_a.get(4002)
        assert final_state.lease_owner_token == winner_token
        assert final_state.fingerprint == winner_fp
        assert final_state.status == AutomationStatus.PROCESSING

    def test_expired_owner_cannot_save_before_reclaim(self, temp_db):
        """Expired owner cannot save state before someone else reclaims."""
        repo = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4003, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=4003, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire Worker A's lease
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 4003)
            )
            conn.commit()

        # Worker B reclaims
        token_b = repo.claim_for_processing(ticket_id=4003, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None
        assert token_b != token_a

        # Worker A (with expired token) tries to save state
        state = AutomationState(
            ticket_id=4003,
            fingerprint=fp,
            status=AutomationStatus.COMPLETED,
            reactivation_completed=True
        )

        result = repo.save(state, owner_token=token_a)
        assert result is False, "Expired owner should not be able to save"

        # Verify Worker B still owns it
        final = repo.get(4003)
        assert final.lease_owner_token == token_b
        assert final.status == AutomationStatus.PROCESSING

    def test_missing_token_cannot_save_after_lease_expiration(self, temp_db):
        """Missing token cannot save after lease expires."""
        repo = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4004, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Claim with token
        token = repo.claim_for_processing(ticket_id=4004, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        # Expire the lease (but token still exists in DB)
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 4004)
            )
            conn.commit()

        # Try to save WITHOUT providing token (even though one exists)
        state = AutomationState(
            ticket_id=4004,
            fingerprint=fp,
            status=AutomationStatus.COMPLETED
        )

        result = repo.save(state, owner_token=None)
        assert result is False, "Missing token should reject save after expiration"

        final = repo.get(4004)
        assert final.status == AutomationStatus.PROCESSING

    def test_wrong_token_cannot_save_after_lease_expiration(self, temp_db):
        """Wrong token cannot save after lease expires."""
        repo = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4005, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=4005, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire lease
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 4005)
            )
            conn.commit()

        # Try to save with wrong token (not reclaimed yet)
        import uuid
        wrong_token = str(uuid.uuid4())

        state = AutomationState(
            ticket_id=4005,
            fingerprint=fp,
            status=AutomationStatus.COMPLETED
        )

        result = repo.save(state, owner_token=wrong_token)
        assert result is False, "Wrong token should reject save after expiration"

        final = repo.get(4005)
        assert final.status == AutomationStatus.PROCESSING
        assert final.lease_owner_token == token_a  # Old token still there

    def test_runner_releases_lease_after_success(self, temp_db):
        """Lease is released (cleared) after successful COMPLETED status."""
        repo = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4006, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Claim ticket
        token = repo.claim_for_processing(ticket_id=4006, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        before = repo.get(4006)
        assert before.processing_lease_until is not None
        assert before.lease_owner_token == token

        # Mark completed (should release lease)
        result = repo.mark_completed(ticket_id=4006, owner_token=token)
        assert result is True

        # Verify lease is released
        after = repo.get(4006)
        assert after.status == AutomationStatus.COMPLETED
        assert after.processing_lease_until is None
        assert after.lease_owner_token is None

    def test_stale_worker_cannot_release_new_owner_lease(self, temp_db):
        """Stale worker cannot clear new owner's lease via mark_completed."""
        repo = AutomationStateRepository(db_path=temp_db)
        ticket = Ticket(id=4007, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=4007, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire and reclaim
        now = datetime.now(timezone.utc)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 4007)
            )
            conn.commit()

        token_b = repo.claim_for_processing(ticket_id=4007, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None
        assert token_b != token_a

        # Worker A (stale) tries to mark completed with old token
        result = repo.mark_completed(ticket_id=4007, owner_token=token_a)
        assert result is False, "Stale worker should not be able to release new owner's lease"

        # Verify Worker B's lease still active
        state = repo.get(4007)
        assert state.status == AutomationStatus.PROCESSING
        assert state.lease_owner_token == token_b
        assert state.processing_lease_until is not None
