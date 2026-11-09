"""Regression test for P2 Issue #5 Task 1: SQLite persistence of ambiguous write fields.

Tests that AutomationStateRepository.save() correctly persists and restores
ambiguous_write_outcome and ambiguous_write_context fields in both owned
and unowned record scenarios.
"""

import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta

from srcs.models import AutomationState, AutomationStatus
from srcs.repositories.automation_state_repository import AutomationStateRepository


class TestAmbiguousWritePersistence:
    """Verify ambiguous write fields persist to SQLite and restore correctly."""

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

    def test_ambiguous_write_fields_persist_on_unowned_insert(self, temp_db):
        """Ambiguous write fields must persist when inserting unowned record."""
        repo = AutomationStateRepository(db_path=temp_db)

        # Create state with ambiguous write outcome
        state = AutomationState(
            ticket_id=1001,
            fingerprint="fp_test_1001",
            status=AutomationStatus.RETRY_SCHEDULED,
            ambiguous_write_outcome="message_post:unknown",
            ambiguous_write_context="Timeout after POST, server may have created note",
        )

        # Save unowned record (no owner_token)
        success = repo.save(state)
        assert success is True

        # Create new repository instance with same database
        repo2 = AutomationStateRepository(db_path=temp_db)

        # Retrieve and verify fields
        retrieved = repo2.get(1001)
        assert retrieved is not None
        assert retrieved.ambiguous_write_outcome == "message_post:unknown"
        assert retrieved.ambiguous_write_context == "Timeout after POST, server may have created note"

    def test_ambiguous_write_fields_persist_on_unowned_update(self, temp_db):
        """Ambiguous write fields must persist when updating unowned record."""
        repo = AutomationStateRepository(db_path=temp_db)

        # Insert initial state without ambiguous fields
        state1 = AutomationState(
            ticket_id=1002,
            fingerprint="fp_test_1002",
            status=AutomationStatus.PROCESSING,
        )
        repo.save(state1)

        # Update with ambiguous write outcome
        state2 = AutomationState(
            ticket_id=1002,
            fingerprint="fp_test_1002",
            status=AutomationStatus.RETRY_SCHEDULED,
            ambiguous_write_outcome="write:unknown",
            ambiguous_write_context="HTTP 503 during stage update, commit unknown",
        )
        success = repo.save(state2)
        assert success is True

        # Retrieve and verify update persisted
        repo2 = AutomationStateRepository(db_path=temp_db)
        retrieved = repo2.get(1002)
        assert retrieved is not None
        assert retrieved.ambiguous_write_outcome == "write:unknown"
        assert retrieved.ambiguous_write_context == "HTTP 503 during stage update, commit unknown"

    def test_ambiguous_write_fields_persist_on_owned_update(self, temp_db):
        """Ambiguous write fields must persist when updating owned record with valid token."""
        repo = AutomationStateRepository(db_path=temp_db)

        # Claim ticket to create owned record
        ticket_id = 1003
        fp = "fp_test_1003"
        token = repo.claim_for_processing(
            ticket_id=ticket_id,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert token is not None

        # Get the claimed state and update with ambiguous fields
        claimed_state = repo.get(ticket_id)
        assert claimed_state is not None

        # Update owned record with ambiguous write outcome
        claimed_state.ambiguous_write_outcome = "message_post:unknown"
        claimed_state.ambiguous_write_context = "Response lost after Odoo created note"
        claimed_state.status = AutomationStatus.RETRY_SCHEDULED

        # Save with valid owner token
        success = repo.save(claimed_state, owner_token=token)
        assert success is True

        # Retrieve and verify fields persisted
        repo2 = AutomationStateRepository(db_path=temp_db)
        retrieved = repo2.get(ticket_id)
        assert retrieved is not None
        assert retrieved.ambiguous_write_outcome == "message_post:unknown"
        assert retrieved.ambiguous_write_context == "Response lost after Odoo created note"

    def test_ambiguous_write_fields_clear_on_success(self, temp_db):
        """Ambiguous write fields must clear when state transitions to success."""
        repo = AutomationStateRepository(db_path=temp_db)

        # Create state with ambiguous outcome
        state1 = AutomationState(
            ticket_id=1004,
            fingerprint="fp_test_1004",
            status=AutomationStatus.RETRY_SCHEDULED,
            ambiguous_write_outcome="message_post:unknown",
            ambiguous_write_context="Timeout on first attempt",
        )
        repo.save(state1)

        # Clear ambiguous fields on retry success
        state2 = AutomationState(
            ticket_id=1004,
            fingerprint="fp_test_1004",
            status=AutomationStatus.COMPLETED,
            ambiguous_write_outcome=None,  # Cleared
            ambiguous_write_context=None,  # Cleared
            odoo_note_completed=True,
            stage_update_completed=True,
        )
        success = repo.save(state2)
        assert success is True

        # Verify fields are now None
        repo2 = AutomationStateRepository(db_path=temp_db)
        retrieved = repo2.get(1004)
        assert retrieved is not None
        assert retrieved.ambiguous_write_outcome is None
        assert retrieved.ambiguous_write_context is None
        assert retrieved.status == AutomationStatus.COMPLETED
