"""P2 Issue #5 Task 1: UNKNOWN safety guard for escalation paths.

Regression tests verifying that persisted UNKNOWN write outcomes prevent
automatic retries of add_log() in both missing-email and normal manual-review paths.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus
from srcs.services.ticket_fingerprinter import TicketFingerprinter


class TestUnknownGuardEscalation:
    """Test UNKNOWN guard prevents automatic retries in escalation paths."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        return tmp_path / "test.db"

    @pytest.fixture
    def verified_verifier(self):
        """Create explicitly VERIFIED mock identity verifier."""
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test verified",
            source="test",
            verified_email=None
        ))
        return verifier

    def test_missing_email_unknown_guard_prevents_retry(self, temp_db, verified_verifier):
        """
        P2 Issue #5 Task 1: UNKNOWN guard for missing-email escalation path.

        Scenario:
        1. First execution: ticket is login issue but has no email
        2. Attempt to post note explaining escalation → UNKNOWN outcome
        3. Persist UNKNOWN to state
        4. Second execution: UNKNOWN guard prevents calling add_log() again
        5. Escalate directly to manual review without posting note

        Assertions:
        - First execution: add_log() called once, returns UNKNOWN
        - Second execution: add_log() not called, escalates with UNKNOWN guard
        - Result: no duplicate note attempt
        """
        ticket_id = 6000
        ticket = Ticket(
            id=ticket_id,
            name="Cannot access system",
            email_from="",  # No email
        )

        state_repo = AutomationStateRepository(db_path=temp_db)
        call_count = {"add_log": 0}

        def add_log_timeout(ticket_id, log_message):
            call_count["add_log"] += 1
            if call_count["add_log"] == 1:
                # First call: timeout (ambiguous)
                from requests.exceptions import Timeout
                raise Timeout("Response timeout")
            else:
                # Should not reach here
                return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket
        ticket_client.add_log.side_effect = add_log_timeout

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=Mock(),
            ticket_analyzer=Mock(
                analyze=Mock(return_value=AnalysisResult(
                    is_login_issue=True,
                    issue_type=IssueType.CANNOT_LOGIN,
                    reason="Login issue",
                    confidence=0.9,
                ))
            ),
            gmail_service=Mock(send_email=Mock(return_value=True)),
            state_repo=state_repo,
            identity_verifier=verified_verifier,
        )

        # First execution: missing email, attempt to post note, get UNKNOWN
        result1 = workflow.execute(ticket_id=ticket_id)
        assert result1.success is False
        assert result1.action_taken == "escalated_manual_review"
        assert result1.ambiguous_write_outcome == "message_post:unknown"
        assert call_count["add_log"] == 1, "First execution should call add_log once"

        # Persist UNKNOWN state (simulating main.py's persistence)
        fingerprint = TicketFingerprinter.generate(ticket)
        state_with_unknown = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            ambiguous_write_outcome="message_post:unknown",
            ambiguous_write_context="Response timeout",
        )
        state_repo.save(state_with_unknown)

        # Read back persisted state
        persisted_state = state_repo.get(ticket_id)
        assert persisted_state is not None
        assert persisted_state.ambiguous_write_outcome == "message_post:unknown"

        # Second execution: UNKNOWN guard should prevent add_log() call
        result2 = workflow.execute(ticket_id=ticket_id, state=persisted_state)

        # Verify UNKNOWN guard triggered
        assert result2.success is False, "Should escalate due to UNKNOWN guard"
        assert result2.action_taken == "escalated_manual_review", \
            f"Expected escalated_manual_review, got {result2.action_taken}"
        assert result2.ambiguous_write_outcome == "message_post:unknown"
        assert call_count["add_log"] == 1, "Second execution should NOT call add_log (UNKNOWN guard)"

    def test_manual_review_unknown_guard_prevents_retry(self, temp_db, verified_verifier):
        """
        P2 Issue #5 Task 1: UNKNOWN guard for normal manual-review escalation path.

        Scenario:
        1. First execution: decision is MANUAL_REVIEW, escalation note posted → UNKNOWN
        2. Persist UNKNOWN to state
        3. Second execution: UNKNOWN guard prevents calling add_log() again
        4. Escalate directly without posting note

        Assertions:
        - First execution: add_log() called once, returns UNKNOWN
        - Second execution: add_log() not called, escalates with UNKNOWN guard
        - Result: no duplicate escalation note attempt
        """
        ticket_id = 6001
        ticket = Ticket(
            id=ticket_id,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP6001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",
            deactivation_reason=None,
        )

        state_repo = AutomationStateRepository(db_path=temp_db)
        call_count = {"add_log": 0}

        def add_log_timeout(ticket_id, log_message):
            call_count["add_log"] += 1
            if call_count["add_log"] == 1:
                # First call: timeout (ambiguous)
                from requests.exceptions import Timeout
                raise Timeout("Response timeout")
            else:
                # Should not reach here
                return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)

        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket
        ticket_client.add_log.side_effect = add_log_timeout

        # Decision service returns MANUAL_REVIEW (e.g., already active employee)
        workflow = LoginWorkflow(
            ticket_client=ticket_client,
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
            state_repo=state_repo,
            identity_verifier=verified_verifier,
        )

        # Mock decision service to return MANUAL_REVIEW
        from srcs.services.decision_service import Decision
        workflow.decision_service.decide = Mock(return_value=Mock(
            action=Decision.MANUAL_REVIEW,
            reason="Employee is already active"
        ))

        # First execution: escalate to manual review, attempt to post note, get UNKNOWN
        result1 = workflow.execute(ticket_id=ticket_id)
        assert result1.success is False
        assert result1.action_taken == "escalated_manual_review"
        assert result1.ambiguous_write_outcome == "message_post:unknown"
        assert call_count["add_log"] == 1, "First execution should call add_log once"

        # Persist UNKNOWN state
        fingerprint = TicketFingerprinter.generate(ticket)
        state_with_unknown = AutomationState(
            ticket_id=ticket_id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            ambiguous_write_outcome="message_post:unknown",
            ambiguous_write_context="Response timeout",
        )
        state_repo.save(state_with_unknown)

        # Read back persisted state
        persisted_state = state_repo.get(ticket_id)
        assert persisted_state is not None
        assert persisted_state.ambiguous_write_outcome == "message_post:unknown"

        # Second execution: UNKNOWN guard should prevent add_log() call
        result2 = workflow.execute(ticket_id=ticket_id, state=persisted_state)

        # Verify UNKNOWN guard triggered
        assert result2.success is False, "Should escalate due to UNKNOWN guard"
        assert result2.action_taken == "escalated_manual_review", \
            f"Expected escalated_manual_review, got {result2.action_taken}"
        assert result2.ambiguous_write_outcome == "message_post:unknown"
        assert call_count["add_log"] == 1, "Second execution should NOT call add_log (UNKNOWN guard)"
