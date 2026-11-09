"""P2 Issue #5 Task 2: Real runner recovery with LoginWorkflow.

Tests that LoginWorkflow properly persists UNKNOWN outcomes to real SQLite
and prevents duplicate Odoo notes when the runner restarts and reconsiders a ticket.

Uses:
- Real temporary SQLite database
- LoginWorkflow.execute()
- Fake Odoo client recording remote notes
- Real ticket fingerprinting
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime, timezone

from srcs.models import Ticket, Employee, EmployeeStatus, DeactivationReason, AutomationState
from srcs.models.automation_state import AutomationStatus
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class FakeOdooTicketClient:
    """Fake Odoo ticket client recording actual remote notes."""

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

    def add_log(self, ticket_id: int, log_message: str) -> WriteOutcome:
        """Record note and simulate timeout on first call."""
        self.call_count["add_log"] += 1

        # Record note as if posted to Odoo
        if ticket_id not in self.notes_posted:
            self.notes_posted[ticket_id] = []
        self.notes_posted[ticket_id].append(log_message)

        # First execution: timeout after posting (UNKNOWN)
        if self.call_count["add_log"] == 1:
            from requests.exceptions import Timeout
            raise Timeout("Response timeout after write")
        else:
            return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

    def update_stage(self, ticket_id: int, stage_id: int) -> WriteOutcome:
        """Stage updates succeed."""
        self.call_count["update_stage"] += 1
        return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

    def get_note_count(self, ticket_id: int) -> int:
        """Get number of notes posted for ticket."""
        return len(self.notes_posted.get(ticket_id, []))


class TestRunnerRecovery:
    """Test runner recovery across restarts with real SQLite persistence."""

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
        hr = Mock()
        hr.get_employee_by_email.return_value = Employee(
            employee_id="EMP7000",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )
        hr.reactivate_lms_account.return_value = True
        return hr

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

    def test_runner_restart_reactivation_path(
        self, temp_db, fake_ticket_client, fake_hr_client, verified_verifier
    ):
        """
        P2 Issue #5 Task 2: Real runner recovery - reactivation path.

        Scenario:
        1. First execution: ticket processed, LMS reactivation succeeds
        2. Odoo note created but response lost (UNKNOWN)
        3. State persisted to real SQLite
        4. Process restarts (new repository instance)
        5. Second execution: loads persisted UNKNOWN, escalates to manual review
        6. Verify: no duplicate note, UNKNOWN remains persisted
        """
        ticket_id = 7000
        ticket = Ticket(
            id=ticket_id,
            name="Cannot login",
            email_from="user@company.com",
        )

        # === FIRST EXECUTION ===
        state_repo_1 = AutomationStateRepository(db_path=temp_db)

        workflow_1 = LoginWorkflow(
            ticket_client=fake_ticket_client,
            hr_client=fake_hr_client,
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_1,
            identity_verifier=verified_verifier,
        )

        result_1 = workflow_1.execute(ticket_id=ticket_id)

        assert result_1.success is False
        assert result_1.action_taken in ["escalated_manual_review", "retry_scheduled"]
        assert fake_ticket_client.get_note_count(ticket_id) == 1
        assert fake_hr_client.reactivate_lms_account.call_count == 1

        # Persist UNKNOWN state
        fingerprint = TicketFingerprinter.generate(ticket)
        state_with_unknown = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,
            ambiguous_write_outcome="message_post:unknown",
            ambiguous_write_context="Response timeout after write",
        )
        state_repo_1.save(state_with_unknown)

        # === SYSTEM RESTART ===
        state_repo_2 = AutomationStateRepository(db_path=temp_db)
        persisted_state = state_repo_2.get(ticket_id)
        assert persisted_state is not None
        assert persisted_state.ambiguous_write_outcome == "message_post:unknown"

        # Reset for second run
        fake_ticket_client.call_count["add_log"] = 0
        fake_hr_client.reactivate_lms_account.reset_mock()

        # === SECOND EXECUTION ===
        workflow_2 = LoginWorkflow(
            ticket_client=fake_ticket_client,
            hr_client=fake_hr_client,
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_2,
            identity_verifier=verified_verifier,
        )

        result_2 = workflow_2.execute(ticket_id=ticket_id, state=persisted_state)

        # === CRITICAL ASSERTIONS ===
        assert result_2.success is False
        assert result_2.action_taken == "escalated_manual_review"
        assert fake_ticket_client.get_note_count(ticket_id) == 1
        assert fake_ticket_client.call_count["add_log"] == 0
        assert fake_hr_client.reactivate_lms_account.call_count == 0

        final_state = state_repo_2.get(ticket_id)
        assert final_state is not None
        assert final_state.ambiguous_write_outcome == "message_post:unknown"

    def test_runner_restart_escalation_path(
        self, temp_db, fake_ticket_client, fake_hr_client, verified_verifier
    ):
        """
        P2 Issue #5 Task 2: Real runner recovery - escalation path.

        Scenario:
        1. First execution: employee already active, escalation path attempts note
        2. Note created but response lost (UNKNOWN)
        3. State persisted to real SQLite
        4. Process restarts
        5. Second execution: loads persisted UNKNOWN, escalates without posting note
        """
        ticket_id = 7001
        ticket = Ticket(
            id=ticket_id,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP7001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None,
        )

        # === FIRST EXECUTION ===
        state_repo_1 = AutomationStateRepository(db_path=temp_db)

        workflow_1 = LoginWorkflow(
            ticket_client=fake_ticket_client,
            hr_client=Mock(get_employee_by_email=Mock(return_value=employee)),
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_1,
            identity_verifier=verified_verifier,
        )

        from srcs.services.decision_service import Decision
        workflow_1.decision_service.decide = Mock(return_value=Mock(
            action=Decision.MANUAL_REVIEW,
            reason="Employee already active"
        ))

        result_1 = workflow_1.execute(ticket_id=ticket_id)
        assert fake_ticket_client.get_note_count(ticket_id) == 1

        # Persist UNKNOWN state
        fingerprint = TicketFingerprinter.generate(ticket)
        state_with_unknown = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            ambiguous_write_outcome="message_post:unknown",
            ambiguous_write_context="Response timeout after write",
        )
        state_repo_1.save(state_with_unknown)

        # === SYSTEM RESTART ===
        state_repo_2 = AutomationStateRepository(db_path=temp_db)
        persisted_state = state_repo_2.get(ticket_id)
        assert persisted_state is not None

        fake_ticket_client.call_count["add_log"] = 0

        # === SECOND EXECUTION ===
        workflow_2 = LoginWorkflow(
            ticket_client=fake_ticket_client,
            hr_client=Mock(get_employee_by_email=Mock(return_value=employee)),
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo_2,
            identity_verifier=verified_verifier,
        )

        workflow_2.decision_service.decide = Mock(return_value=Mock(
            action=Decision.MANUAL_REVIEW,
            reason="Employee already active"
        ))

        result_2 = workflow_2.execute(ticket_id=ticket_id, state=persisted_state)

        # === CRITICAL ASSERTIONS ===
        assert result_2.success is False
        assert result_2.action_taken == "escalated_manual_review"
        assert fake_ticket_client.get_note_count(ticket_id) == 1
        assert fake_ticket_client.call_count["add_log"] == 0
