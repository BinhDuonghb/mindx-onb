"""Tests for lease ownership and stale worker protection.

Verifies that stale workers cannot modify automation state after another worker takes ownership.
"""

import pytest
import tempfile
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from srcs.models import AutomationState, AutomationStatus
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.models import Ticket


class TestLeaseOwnership:
    """Test lease ownership and stale worker protection."""

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

    def test_only_one_worker_can_claim_ticket(self, temp_db):
        """Only one worker can claim a ticket at a time."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1001, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=1001, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Worker B tries to claim (should fail)
        token_b = repo.claim_for_processing(ticket_id=1001, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is None  # Claim blocked

        # Verify Worker A's token is stored
        state = repo.get(1001)
        assert state.lease_owner_token == token_a

    def test_stale_worker_cannot_overwrite_state(self, temp_db):
        """Stale worker cannot update state after losing lease."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1002, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=1002, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Get state after claim
        state_a = repo.get(1002)
        assert state_a.lease_owner_token == token_a
        assert state_a.status == AutomationStatus.PROCESSING

        # Manually expire Worker A's lease
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 1002)
            )
            conn.commit()

        # Worker B claims (new owner)
        token_b = repo.claim_for_processing(ticket_id=1002, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None
        assert token_b != token_a

        # Verify Worker B is now the owner
        state_b = repo.get(1002)
        assert state_b.lease_owner_token == token_b

    def test_stale_worker_cannot_mark_completed(self, temp_db):
        """Stale worker cannot mark ticket completed with old token."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1003, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=1003, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire Worker A's lease
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 1003)
            )
            conn.commit()

        # Worker B claims
        token_b = repo.claim_for_processing(ticket_id=1003, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None

        # Worker A (stale) tries to mark completed with old token
        result_a = repo.mark_completed(ticket_id=1003, owner_token=token_a)
        assert result_a is False  # Should be rejected

        # Verify ticket is still PROCESSING with Worker B's token
        state = repo.get(1003)
        assert state.status == AutomationStatus.PROCESSING
        assert state.lease_owner_token == token_b

        # Worker B (current owner) can mark completed
        result_b = repo.mark_completed(ticket_id=1003, owner_token=token_b)
        assert result_b is True

        # Verify ticket is now completed
        state = repo.get(1003)
        assert state.status == AutomationStatus.COMPLETED
        assert state.lease_owner_token is None

    def test_stale_worker_cannot_release_lease(self, temp_db):
        """Stale worker cannot release another worker's lease via schedule_retry."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1004, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=1004, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire Worker A's lease
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 1004)
            )
            conn.commit()

        # Worker B claims
        token_b = repo.claim_for_processing(ticket_id=1004, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None

        # Verify Worker B has active lease
        state_b = repo.get(1004)
        assert state_b.lease_owner_token == token_b

        # Worker A tries to schedule retry (should not clear Worker B's lease)
        # Note: schedule_retry needs owner_token parameter for Issue 2 fix
        result_a = repo.schedule_retry(ticket_id=1004, retry_after_seconds=3600, owner_token=token_a)
        assert result_a is False  # Should be rejected

        # Verify Worker B's lease is still active
        state_after = repo.get(1004)
        assert state_after.lease_owner_token == token_b
        assert state_after.status == AutomationStatus.PROCESSING

    def test_valid_owner_can_update_state(self, temp_db):
        """Current lease owner can update state normally."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1005, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker claims
        token = repo.claim_for_processing(ticket_id=1005, fingerprint=fp, lease_duration_seconds=300)
        assert token is not None

        # Update state with valid token
        state = AutomationState(
            ticket_id=1005,
            fingerprint=fp,
            status=AutomationStatus.PROCESSING,
            last_decision="processing",
        )
        state.lease_owner_token = token

        # Save should succeed (pass owner_token for active lease validation)
        result = repo.save(state, owner_token=token)
        assert result is True

        # Mark completed with valid token
        result = repo.mark_completed(ticket_id=1005, owner_token=token)
        assert result is True

        # Verify final state
        state_final = repo.get(1005)
        assert state_final.status == AutomationStatus.COMPLETED
        assert state_final.lease_owner_token is None

    def test_schedule_retry_validates_ownership(self, temp_db):
        """schedule_retry must validate ownership token."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1006, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker A claims
        token_a = repo.claim_for_processing(ticket_id=1006, fingerprint=fp, lease_duration_seconds=300)
        assert token_a is not None

        # Expire and reclaim
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 1006)
            )
            conn.commit()

        # Worker B claims
        token_b = repo.claim_for_processing(ticket_id=1006, fingerprint=fp, lease_duration_seconds=300)
        assert token_b is not None

        # Worker A tries to schedule retry with old token
        result = repo.schedule_retry(ticket_id=1006, retry_after_seconds=3600, owner_token=token_a)
        assert result is False

        # Worker B can schedule retry with valid token
        result = repo.schedule_retry(ticket_id=1006, retry_after_seconds=3600, owner_token=token_b)
        assert result is True

        # Verify state transitioned
        state = repo.get(1006)
        assert state.status == AutomationStatus.RETRY_SCHEDULED

    def test_concurrent_claim_attempts(self, temp_db):
        """Multiple threads cannot claim same ticket concurrently."""
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=1007, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        tokens = []
        lock = threading.Lock()

        def worker_claim(worker_id):
            token = repo.claim_for_processing(ticket_id=1007, fingerprint=fp, lease_duration_seconds=300)
            if token:
                with lock:
                    tokens.append((worker_id, token))

        # Start 3 threads trying to claim the same ticket
        threads = [threading.Thread(target=worker_claim, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should have succeeded
        assert len(tokens) == 1, f"Expected 1 successful claim, got {len(tokens)}"

        # Verify the winner's token is stored
        state = repo.get(1007)
        assert state.lease_owner_token == tokens[0][1]
