"""Regression test for P2 Issue #5 Task 4: Real restart safety.

Tests that after a timeout following a successful Odoo POST, the note is not duplicated
when the system restarts and the ticket is reconsidered. Uses a fake Odoo transport
that records actual remote notes to verify commit count.
"""

import pytest
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class FakeOdooTransport:
    """Fake Odoo transport that records actual note posts for verification."""

    def __init__(self):
        """Initialize transport with note tracking."""
        self.notes_posted = {}  # ticket_id -> list of note messages

    def record_note(self, ticket_id: int, message: str):
        """Record a note as if posted to Odoo."""
        if ticket_id not in self.notes_posted:
            self.notes_posted[ticket_id] = []
        self.notes_posted[ticket_id].append(message)

    def get_note_count(self, ticket_id: int) -> int:
        """Get number of notes posted for ticket."""
        return len(self.notes_posted.get(ticket_id, []))

    def get_notes(self, ticket_id: int) -> list:
        """Get all notes for ticket."""
        return self.notes_posted.get(ticket_id, [])


class TestRestartSafety:
    """Verify UNKNOWN outcome prevents duplicate notes after restart."""

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
        """Create state repository."""
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def fake_transport(self):
        """Create fake Odoo transport."""
        return FakeOdooTransport()

    def test_timeout_after_successful_post_no_duplicate_on_restart(self, state_repo, fake_transport):
        """
        P2 Issue #5 Task 4: Simulate timeout after successful Odoo POST.

        Scenario:
        1. Odoo creates one note successfully
        2. Network timeout before response returns (response lost)
        3. Workflow records UNKNOWN outcome in SQLite
        4. System restarts, reads persisted UNKNOWN state
        5. Retry attempts reactivation again
        6. Verify: remote note count remains 1 (no duplicate)

        This test verifies the core safety guarantee: ambiguous write outcomes
        prevent duplicate side effects when the system restarts.
        """
        ticket_id = 5000
        ticket = Ticket(
            id=ticket_id,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP5000",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # === FIRST ATTEMPT: Timeout after Odoo successfully creates note ===
        verifier1 = Mock(spec=IdentityVerifier)
        verifier1.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test verified",
            source="test",
            verified_email=None
        ))

        # Create mock ticket_client that simulates timeout after successful Odoo POST
        ticket_client1 = Mock()
        ticket_client1.get_ticket.return_value = ticket

        # Simulate: Odoo successfully creates note, then we get timeout
        def add_log_with_timeout(ticket_id, log_message):
            # Record note as if posted to Odoo (before timeout occurs)
            fake_transport.record_note(ticket_id, log_message)
            # Then raise timeout (response lost)
            raise Timeout("Response timeout after write")

        ticket_client1.add_log.side_effect = add_log_with_timeout
        ticket_client1.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

        workflow1 = LoginWorkflow(
            ticket_client=ticket_client1,
            hr_client=Mock(get_employee_by_email=Mock(return_value=employee),
                         reactivate_lms_account=Mock(return_value=True)),
            ticket_analyzer=Mock(analyze=Mock(return_value=AnalysisResult(
                is_login_issue=True,
                issue_type=IssueType.CANNOT_LOGIN,
                reason="Login issue",
                confidence=0.9,
            ))),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo,
            identity_verifier=verifier1,
        )

        # First execution: note posted to Odoo, then timeout
        result1 = workflow1.execute(ticket_id=ticket_id)

        # Verify first attempt resulted in UNKNOWN outcome
        assert result1.action_taken == "escalated_manual_review"
        assert result1.ambiguous_write_outcome == "message_post:unknown"
        assert result1.odoo_note_completed is False  # Note was ambiguous

        # Verify note was posted to fake Odoo
        assert fake_transport.get_note_count(ticket_id) == 1
        notes_before = fake_transport.get_notes(ticket_id)

        # Manually persist state with ambiguous outcome (simulating main.py's state persistence)
        from srcs.models.automation_state import AutomationStatus
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        fingerprint = TicketFingerprinter.generate(ticket)
        saved_state = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,
            odoo_note_completed=False,
            ambiguous_write_outcome=result1.ambiguous_write_outcome or "message_post:unknown",
            ambiguous_write_context="Response timeout after write",
        )
        state_repo.save(saved_state)

        # Verify state was persisted
        assert saved_state is not None
        assert saved_state.ambiguous_write_outcome is not None  # UNKNOWN was persisted

        # === SYSTEM RESTART: Read persisted state ===
        # Create new repository instance (simulating fresh process after restart)
        state_repo_after_restart = AutomationStateRepository(db_path=state_repo.db_path)

        # Retrieve persisted UNKNOWN state
        retrieved_state = state_repo_after_restart.get(ticket_id)
        assert retrieved_state is not None
        assert retrieved_state.ambiguous_write_outcome is not None  # Still has UNKNOWN

        # === SECOND ATTEMPT: Retry with persisted state ===
        verifier2 = Mock(spec=IdentityVerifier)
        verifier2.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test verified",
            source="test",
            verified_email=None
        ))

        ticket_client2 = Mock()
        ticket_client2.get_ticket.return_value = ticket

        # Second attempt succeeds
        def add_log_success(ticket_id, log_message):
            fake_transport.record_note(ticket_id, log_message)
            return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

        ticket_client2.add_log.side_effect = add_log_success
        ticket_client2.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

        workflow2 = LoginWorkflow(
            ticket_client=ticket_client2,
            hr_client=Mock(get_employee_by_email=Mock(return_value=employee),
                         reactivate_lms_account=Mock(return_value=True)),
            ticket_analyzer=Mock(analyze=Mock(return_value=AnalysisResult(
                is_login_issue=True,
                issue_type=IssueType.CANNOT_LOGIN,
                reason="Login issue",
                confidence=0.9,
            ))),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_after_restart,
            identity_verifier=verifier2,
        )

        # Second execution with persisted state (after restart)
        result2 = workflow2.execute(ticket_id=ticket_id, state=retrieved_state)

        # === VERIFICATION ===
        # With UNKNOWN guard in place (P2 Issue #5 Task 1), second execution should escalate
        # to manual review, NOT retry the operation
        assert result2.success is False, \
            f"Second execution should fail due to UNKNOWN guard. Got: {result2.message}"
        assert result2.action_taken == "escalated_manual_review", \
            f"Expected escalated_manual_review (UNKNOWN guard), got {result2.action_taken}"

        # CRITICAL: Verify no duplicate note was created
        # Should still be 1 note total (from first attempt timeout)
        # NOT 2 (which would occur without the UNKNOWN guard)
        notes_after = fake_transport.get_notes(ticket_id)
        assert fake_transport.get_note_count(ticket_id) == 1, \
            f"Expected 1 note (no duplicate from UNKNOWN guard), got {fake_transport.get_note_count(ticket_id)}: {notes_after}"
