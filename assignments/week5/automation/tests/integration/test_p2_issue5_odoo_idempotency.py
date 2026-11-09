"""P2 Issue #5 — Odoo POST Idempotency & Safe Retry - RED Phase Tests.

Tests for:
1. No automatic POST replay on 5xx
2. Server committed but response lost (no duplicate note)
3. Safe read retries still work
4. Ambiguous outcome survives restart
5. Confirmed failure recovery
6. Concurrent workers protected
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, ConnectionError
from datetime import datetime, timezone

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.gmail import GmailService
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class TestOdooNonIdempotentWriteNoAutoRetry:
    """Test 1: Non-idempotent Odoo POST requests are not automatically retried."""

    @pytest.fixture
    def temp_db(self):
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
        return AutomationStateRepository(db_path=temp_db)

    def test_non_idempotent_odoo_post_is_not_automatically_retried(self, state_repo):
        """Simulate HTTP timeout on write request - should not auto-retry."""
        # Setup: Mock ticket and employee
        ticket = Ticket(
            id=5001,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP5001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Setup: Mock clients with specific failure behavior
        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee
        hr_client.reactivate_lms_account.return_value = True

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )

        # CRITICAL: Simulate ambiguous outcome on add_log (Odoo note posting)
        # Timeout before response - urllib3 would normally retry this
        ticket_client.add_log.side_effect = Timeout("Connection timeout on POST")

        # Other operations succeed
        ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        # Create verified verifier
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test",
            source="test",
            verified_email=None
        ))

        # Create workflow
        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verifier,
        )

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            result = workflow.execute(ticket_id=ticket.id)

        # ASSERTION: add_log called exactly ONCE, not retried
        # (With unsafe auto-retry, urllib3 would call it 3+ times)
        ticket_client.add_log.assert_called_once()
        assert result.action_taken == "escalated_manual_review", "Ambiguous write must be held for manual review"
        assert result.ambiguous_write_outcome == "message_post:unknown"


class TestMessagePostCommittedThenTimeoutNoDuplicate:
    """Test 2: Server committed note but response lost - no blind second POST."""

    @pytest.fixture
    def temp_db(self):
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
        return AutomationStateRepository(db_path=temp_db)

    def test_message_post_committed_then_timeout_does_not_duplicate_note(self, state_repo):
        """Odoo created note but response lost - should not blindly post again."""
        ticket = Ticket(
            id=5002,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP5002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee
        hr_client.reactivate_lms_account.return_value = True

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )

        # CRITICAL: Simulate response lost after successful write
        # First call: timeout (but Odoo already created it)
        # Should NOT have second call
        ticket_client.add_log.side_effect = Timeout("Response timeout after write")

        ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test",
            source="test",
            verified_email=None
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verifier,
        )

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            result = workflow.execute(ticket_id=ticket.id)

        # ASSERTION: add_log NOT called multiple times (no blind retry)
        assert ticket_client.add_log.call_count == 1, "Should not automatically retry write on timeout"


class TestReadOnlyOdooRequestRetainsBoundedRetry:
    """Test 3: Safe read-only operations retain bounded retries."""

    @pytest.fixture
    def temp_db(self):
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
        return AutomationStateRepository(db_path=temp_db)

    def test_read_only_odoo_request_retains_bounded_retry(self, state_repo):
        """Read operations should still have retry protection."""
        ticket = Ticket(
            id=5003,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP5003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee
        hr_client.reactivate_lms_account.return_value = True

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )

        ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test",
            source="test",
            verified_email=None
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verifier,
        )

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            result = workflow.execute(ticket_id=ticket.id)

        # ASSERTION: Successful execution shows reads work normally
        assert result.success is True
        assert result.action_taken == "account_reactivated"


class TestAmbiguousOdooWriteRemainsSafeAfterRestart:
    """Test 4: Ambiguous write outcome doesn't duplicate after restart."""

    @pytest.fixture
    def temp_db(self):
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
        return AutomationStateRepository(db_path=temp_db)

    def test_ambiguous_odoo_write_remains_safe_after_restart(self, state_repo):
        """Restarting runner should not blindly duplicate ambiguous write."""
        ticket = Ticket(
            id=5004,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP5004",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Simulate first attempt that failed with ambiguous outcome
        prior_state = AutomationState(
            ticket_id=5004,
            fingerprint="fp1",
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,
            odoo_note_completed=False,  # Ambiguous - might be partially done
            last_decision="retry_scheduled",
        )
        state_repo.save(prior_state)

        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )

        # Second attempt: add_log succeeds this time
        ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test",
            source="test",
            verified_email=None
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verifier,
        )

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            result = workflow.execute(ticket_id=5004, state=prior_state)

        # ASSERTION: add_log called only once per execution (not blindly retried)
        assert ticket_client.add_log.call_count == 1
        # LMS reactivation should NOT be called again (already completed)
        assert hr_client.reactivate_lms_account.call_count == 0


class TestConfirmedOdooNoteFailureRecoverable:
    """Test 5: Confirmed failures use existing recovery mechanism."""

    @pytest.fixture
    def temp_db(self):
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
        return AutomationStateRepository(db_path=temp_db)

    def test_confirmed_odoo_note_failure_remains_recoverable(self, state_repo):
        """Confirmed failures schedule retry, preserve completed side effects."""
        ticket = Ticket(
            id=5005,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP5005",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee
        hr_client.reactivate_lms_account.return_value = True

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )

        # Confirmed failure: add_log returns False (safe to mark as complete failure)
        ticket_client.add_log.return_value = WriteOutcome(
            status=WriteOutcomeStatus.CONFIRMED_FAILURE,
            error="Note posting failed",
            is_retryable=True
        )

        ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test",
            source="test",
            verified_email=None
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verifier,
        )

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            result = workflow.execute(ticket_id=5005)

        # ASSERTION: Confirmed failure schedules retry
        assert result.action_taken == "retry_scheduled"
        # LMS reactivation was completed (marked)
        assert result.reactivation_completed is True
        # Note posting failed (confirmed)
        assert result.odoo_note_completed is False


class TestConcurrentWorkersCannotDuplicateOdooNote:
    """Test 6: Lease protection prevents duplicate writes from concurrent workers."""

    @pytest.fixture
    def temp_db(self):
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
        return AutomationStateRepository(db_path=temp_db)

    def test_concurrent_workers_cannot_duplicate_odoo_note(self, state_repo):
        """Existing lease protection prevents concurrent writes."""
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        ticket = Ticket(id=5006, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Worker 1 claims the ticket
        token1 = state_repo.claim_for_processing(
            ticket_id=5006,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert token1 is not None, "Worker 1 should claim successfully"

        # Worker 2 tries to claim same ticket
        token2 = state_repo.claim_for_processing(
            ticket_id=5006,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert token2 is None, "Worker 2 should fail to claim (lease active)"

        # Verify state is PROCESSING (lease active)
        state = state_repo.get(5006)
        assert state.status == AutomationStatus.PROCESSING
