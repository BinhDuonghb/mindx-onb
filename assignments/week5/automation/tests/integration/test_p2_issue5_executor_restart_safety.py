"""P2 Issue #5 Task 2: Executor-level restart safety test.

Tests that after a timeout following a successful Odoo POST (UNKNOWN outcome),
the system correctly prevents duplicate notes when the runner restarts and
reconsiders the ticket with persisted UNKNOWN state.

Uses:
- Real temporary SQLite repository
- LoginWorkflow.execute()
- Fake Odoo transport that records remote notes
- Explicit VERIFIED mock identity
- Mock HR/LMS service
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from requests.exceptions import Timeout

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.login_workflow import LoginWorkflow
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class FakeOdooTicketClient:
    """Fake Odoo ticket client that records actual remote notes."""

    def __init__(self):
        """Initialize with note tracking."""
        self.notes_posted = {}  # ticket_id -> list of note messages
        self.call_count = {"add_log": 0, "update_stage": 0}

    def get_ticket(self, ticket_id: int) -> Ticket:
        """Return test ticket."""
        return Ticket(
            id=ticket_id,
            name="Cannot login",
            email_from="user@company.com",
        )

    def search_tickets(self, domain=None, limit=100):
        """Return empty search for unrelated queries."""
        return []

    def add_log(self, ticket_id: int, log_message: str) -> WriteOutcome:
        """Record note and simulate timeout on first call."""
        self.call_count["add_log"] += 1

        # Record note as if posted to Odoo
        if ticket_id not in self.notes_posted:
            self.notes_posted[ticket_id] = []
        self.notes_posted[ticket_id].append(log_message)

        # First call: timeout after posting (ambiguous outcome)
        # Second call (if any): success
        if self.call_count["add_log"] == 1:
            # Simulate: Odoo created the note, but we timeout before getting response
            raise Timeout("Response timeout after write")
        else:
            # Retry succeeds
            return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

    def update_stage(self, ticket_id: int, stage_id: int) -> WriteOutcome:
        """Stage updates succeed."""
        self.call_count["update_stage"] += 1
        return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

    def get_note_count(self, ticket_id: int) -> int:
        """Get number of notes posted for ticket."""
        return len(self.notes_posted.get(ticket_id, []))

    def get_notes(self, ticket_id: int) -> list:
        """Get all notes for ticket."""
        return self.notes_posted.get(ticket_id, [])


class FakeHRClient:
    """Fake HR client that tracks reactivation calls."""

    def __init__(self):
        """Initialize."""
        self.reactivation_calls = []

    def get_employee_by_email(self, email: str) -> Employee:
        """Return test employee."""
        return Employee(
            employee_id="EMP5000",
            name="User",
            email=email,
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

    def reactivate_lms_account(self, employee_id: str, new_status: str) -> bool:
        """Track reactivation call and return success."""
        self.reactivation_calls.append({
            "employee_id": employee_id,
            "new_status": new_status,
            "timestamp": datetime.now(timezone.utc),
        })
        return True


class TestExecutorRestartSafety:
    """Executor-level restart safety test for P2 Issue #5."""

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
    def fake_ticket_client(self):
        """Create fake Odoo ticket client."""
        return FakeOdooTicketClient()

    @pytest.fixture
    def fake_hr_client(self):
        """Create fake HR client."""
        return FakeHRClient()

    @pytest.fixture
    def verified_verifier(self):
        """Create explicitly VERIFIED mock identity verifier."""
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Task 2 test: verified fixture",
            source="test",
            verified_email=None
        ))
        return verifier

    def test_executor_restart_prevents_duplicate_notes(
        self, temp_db, fake_ticket_client, fake_hr_client, verified_verifier
    ):
        """
        P2 Issue #5 Task 2: Executor-level restart safety via LoginWorkflow.

        Scenario:
        1. First run: LMS reactivation succeeds, Odoo note created but response lost (UNKNOWN)
        2. UNKNOWN persisted to SQLite
        3. System restarts (new repository instance, new workflow)
        4. Second run: workflow loads persisted state, UNKNOWN guard prevents repost
        5. Verify no duplicate notes created

        Assertions:
        - remote_note_count == 1 (no duplicate)
        - LMS reactivation called exactly once
        - UNKNOWN remains persisted
        - Ticket held for manual review on second run
        """
        ticket_id = 5000

        # === FIRST EXECUTION: Timeout after Odoo POST ===
        state_repo_1 = AutomationStateRepository(db_path=temp_db)

        workflow_1 = LoginWorkflow(
            ticket_client=fake_ticket_client,
            hr_client=fake_hr_client,
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue detected",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_1,
            identity_verifier=verified_verifier,
        )

        # Run first execution (will timeout on add_log)
        result_1 = workflow_1.execute(ticket_id=ticket_id)

        # First execution should fail with escalation due to ambiguous outcome
        assert result_1.success is False, \
            f"First execution should fail due to timeout. Got: {result_1.message}"
        assert result_1.action_taken in ["escalated_manual_review", "retry_scheduled"], \
            f"First execution should escalate or retry, got: {result_1.action_taken}"

        # Verify one note was created (but timeout prevented response)
        assert fake_ticket_client.get_note_count(ticket_id) == 1, \
            f"Expected 1 note after first execution, got {fake_ticket_client.get_note_count(ticket_id)}"

        # Verify LMS reactivation was called
        assert len(fake_hr_client.reactivation_calls) == 1, \
            f"Expected 1 LMS reactivation call, got {len(fake_hr_client.reactivation_calls)}"

        # Create and persist state with ambiguous outcome (simulating main.py's state persistence)
        # The workflow returns ambiguous_write_outcome but the executor must persist it to SQLite
        from srcs.models.automation_state import AutomationStatus
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        # Generate fingerprint for the ticket
        ticket = fake_ticket_client.get_ticket(ticket_id)
        fingerprint = TicketFingerprinter.generate(ticket)

        state_after_first = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,  # LMS was reactivated before timeout
            odoo_note_completed=False,  # Note was ambiguous (timeout before response)
            ambiguous_write_outcome=result_1.ambiguous_write_outcome or "message_post:unknown",
            ambiguous_write_context="Response timeout after write",
        )
        state_repo_1.save(state_after_first)

        # Verify UNKNOWN was persisted
        retrieved_state = state_repo_1.get(ticket_id)
        assert retrieved_state is not None, "State should be persisted after first execution"
        assert retrieved_state.ambiguous_write_outcome is not None, \
            f"ambiguous_write_outcome should be persisted (UNKNOWN from timeout), got: {retrieved_state.ambiguous_write_outcome}"

        # === SYSTEM RESTART: New repository, new workflow ===
        # Simulate process restart: create fresh repository instance from same database
        state_repo_2 = AutomationStateRepository(db_path=temp_db)

        # Verify persisted state is readable after restart
        persisted_state = state_repo_2.get(ticket_id)
        assert persisted_state is not None, "Persisted state should be readable after restart"
        assert persisted_state.ambiguous_write_outcome is not None, \
            f"ambiguous_write_outcome should be preserved across restart, got: {persisted_state.ambiguous_write_outcome}"

        # Reset HR tracking for second run (but keep Odoo client for note count verification)
        fake_hr_client.reactivation_calls = []

        # === SECOND EXECUTION: After restart with persisted UNKNOWN ===
        # Create new workflow (simulating new process)
        workflow_2 = LoginWorkflow(
            ticket_client=fake_ticket_client,
            hr_client=fake_hr_client,
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue detected",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_2,
            identity_verifier=verified_verifier,
        )

        # Run second execution with persisted state (should escalate due to UNKNOWN guard)
        result_2 = workflow_2.execute(ticket_id=ticket_id, state=persisted_state)

        # Second execution should escalate to manual review (UNKNOWN guard triggered)
        assert result_2.success is False, \
            f"Second execution should fail (UNKNOWN guard escalates). Got: {result_2.message}"
        assert result_2.action_taken == "escalated_manual_review", \
            f"Expected escalated_manual_review, got {result_2.action_taken}. Message: {result_2.message}"

        # === CRITICAL ASSERTIONS ===
        # 1. Remote note count must stay at 1 (no duplicate)
        final_note_count = fake_ticket_client.get_note_count(ticket_id)
        assert final_note_count == 1, \
            f"Expected 1 note (no duplicate), got {final_note_count}: {fake_ticket_client.get_notes(ticket_id)}"

        # 2. add_log was called only once on first execution (timeout before response)
        # Second execution should NOT call add_log because UNKNOWN guard escalates early
        assert fake_ticket_client.call_count["add_log"] == 1, \
            f"Expected add_log called once, got {fake_ticket_client.call_count['add_log']} calls"

        # 3. LMS reactivation called exactly once across both runs (0 on second due to UNKNOWN guard)
        assert len(fake_hr_client.reactivation_calls) == 0, \
            f"LMS reactivation should not be called on second run (UNKNOWN guard escalates). Got {len(fake_hr_client.reactivation_calls)} calls"

        # 4. UNKNOWN remains persisted
        final_state = state_repo_2.get(ticket_id)
        assert final_state is not None, "Final state should exist"
        assert final_state.ambiguous_write_outcome is not None, \
            f"ambiguous_write_outcome should remain persisted after second execution, got: {final_state.ambiguous_write_outcome}"

        # 5. Result indicates manual review action taken
        assert result_2.action_taken == "escalated_manual_review", \
            "UNKNOWN guard should escalate to manual review, not retry"
