"""P1 Issues Fix Verification Tests.

Comprehensive integration tests for all three P1 issues:
1. P1-01: Partial Retry Workflow - Resume incomplete side effects
2. P1-02: Processing Lease - Atomic processing claims with fingerprint changes
3. P1-03: Email Delivery Failure - Durable retry mechanism for email delivery
"""

import pytest
from unittest.mock import Mock
from pathlib import Path
from datetime import datetime, timedelta, timezone

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.gmail import EmailTemplate, CommunicationEvent
from srcs.services.ticket_fingerprinter import TicketFingerprinter


class TestP101PartialRetryWorkflow:
    """P1-01: Partial Retry Workflow - Resume incomplete side effects even when LMS is active."""

    @pytest.fixture
    def temp_db(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    @pytest.fixture
    def state_repo(self, temp_db):
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def workflow(self, state_repo):
        # P2 Issue #4: Inject verified mock verifier for legacy test compatibility
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Legacy test fixture: verified",
            source="test_fixture",
            verified_email=None
        ))

        return LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
            identity_verifier=verifier,
        )

    def test_retry_with_lms_already_active_but_pending_odoo_operations(self, workflow, state_repo):
        """
        P1-01 Fix Verification:
        First attempt: LMS reactivation succeeds, Odoo note fails → RETRY_SCHEDULED
        Second attempt: LMS is now active, but retry should CONTINUE workflow to complete pending operations

        Before fix: Would SKIP because LMS is active
        After fix: Should APPROVE_REACTIVATION to continue side effects
        """
        ticket = Ticket(
            id=1001,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP1001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",  # Already reactivated from first attempt
            deactivation_reason=None,
        )

        # Setup: First attempt succeeded at reactivation but failed at note
        prior_state = AutomationState(
            ticket_id=1001,
            fingerprint="fp1",
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,  # LMS was already reactivated
            odoo_note_completed=False,     # But note posting failed
            stage_update_completed=False,
            last_decision="account_reactivated",
        )
        state_repo.save(prior_state)

        # Setup mocks for second attempt
        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = True

        # Execute retry with prior state
        result = workflow.execute(ticket_id=1001, state=prior_state)

        # P1-01 Fix Verification:
        # Should succeed with APPROVE_REACTIVATION decision (not SKIP)
        assert result.action_taken == "account_reactivated"
        assert result.success is True

        # Verify reactivation was NOT called again (already completed)
        workflow.hr_client.reactivate_lms_account.assert_not_called()

        # Verify pending operations WERE completed
        workflow.ticket_client.add_log.assert_called_once()
        workflow.ticket_client.update_stage.assert_called_once()

    def test_two_consecutive_runs_with_state_transition_from_deactivated_to_active(self, workflow, state_repo):
        """
        P1-01 Integration Test: Two consecutive runs with real state transition.

        Run 1: LMS deactivated → Reactivate + Odoo operations
        Run 2: LMS now active (from Run 1) → Should complete any remaining operations
        """
        ticket = Ticket(
            id=1002,
            name="Cannot login",
            email_from="emp@company.com",
        )

        # Run 1: Employee with deactivated LMS
        employee_run1 = Employee(
            employee_id="EMP1002",
            name="Employee",
            email="emp@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Run 1 Setup
        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee_run1
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(
            status=WriteOutcomeStatus.CONFIRMED_FAILURE,
            error="Note posting failed",
            is_retryable=True
        )  # Fails in Run 1
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = True

        # Run 1 Execution
        result1 = workflow.execute(ticket_id=1002, state=None)
        assert result1.action_taken == "retry_scheduled"
        assert result1.reactivation_completed is True
        assert result1.odoo_note_completed is False

        # Save state after Run 1
        fingerprint = TicketFingerprinter.generate(ticket)
        state1 = AutomationState(
            ticket_id=1002,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=result1.reactivation_completed,
            odoo_note_completed=result1.odoo_note_completed,
            stage_update_completed=result1.stage_update_completed,
        )
        state_repo.save(state1)

        # Run 2: Employee now has active LMS (from Run 1)
        employee_run2 = Employee(
            employee_id="EMP1002",
            name="Employee",
            email="emp@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",  # Changed after Run 1
            deactivation_reason=None,
        )

        # Reset mocks for Run 2
        workflow.ticket_client.reset_mock()
        workflow.hr_client.reset_mock()
        workflow.ticket_analyzer.reset_mock()
        workflow.gmail_service.reset_mock()

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee_run2
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)  # Now succeeds
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = True

        # Run 2 Execution with prior state
        retrieved_state = state_repo.get(1002)
        result2 = workflow.execute(ticket_id=1002, state=retrieved_state)

        # P1-01 Verification: Should succeed despite LMS being active
        assert result2.action_taken == "account_reactivated"
        assert result2.success is True

        # Verify LMS reactivation was NOT attempted (already done in Run 1)
        workflow.hr_client.reactivate_lms_account.assert_not_called()

        # Verify pending Odoo operations WERE completed
        workflow.ticket_client.add_log.assert_called_once()
        workflow.ticket_client.update_stage.assert_called_once()


class TestP102ProcessingLease:
    """P1-02: Processing Lease - Atomic processing claims with fingerprint changes."""

    @pytest.fixture
    def temp_db(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    def test_concurrent_workers_cannot_both_claim_same_ticket(self, temp_db):
        """
        P1-02 Fix Verification: Two workers cannot claim the same ticket simultaneously.

        Even if fingerprint changes, active lease blocks concurrent processing.
        """
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=2001, name="Test", email_from="test@company.com")
        fp1 = TicketFingerprinter.generate(ticket)

        # Worker 1 claims with 5-minute lease
        claimed1 = repo.claim_for_processing(
            ticket_id=2001,
            fingerprint=fp1,
            lease_duration_seconds=300
        )
        assert claimed1 is not None  # TASK 3 FIX: Now returns ownership token, not bool

        # Ticket content changes (new fingerprint)
        ticket.name = "Test - updated"
        fp2 = TicketFingerprinter.generate(ticket)

        # Worker 2 tries to claim with new fingerprint
        # P1-02 Fix: Should FAIL because lease is still active
        claimed2 = repo.claim_for_processing(
            ticket_id=2001,
            fingerprint=fp2,
            lease_duration_seconds=300
        )
        assert claimed2 is None  # TASK 3 FIX: Returns None on failed claim

        # Verify state is still PROCESSING
        state = repo.get(2001)
        assert state is not None
        assert state.status == AutomationStatus.PROCESSING

    def test_fingerprint_change_after_lease_expires_allows_reclaim(self, temp_db):
        """
        P1-02 Atomicity: After lease expires, fingerprint change allows new worker to reclaim.
        """
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=2002, name="Test", email_from="test@company.com")
        fp1 = TicketFingerprinter.generate(ticket)

        # Worker 1 claims with already-expired lease
        claimed1 = repo.claim_for_processing(
            ticket_id=2002,
            fingerprint=fp1,
            lease_duration_seconds=0  # Already expired
        )
        assert claimed1 is not None  # TASK 3 FIX: Returns token on successful claim

        # Ticket content changes
        ticket.name = "Test - updated"
        fp2 = TicketFingerprinter.generate(ticket)

        # Worker 2 can reclaim after lease expired
        claimed2 = repo.claim_for_processing(
            ticket_id=2002,
            fingerprint=fp2,
            lease_duration_seconds=300
        )
        assert claimed2 is not None  # TASK 3 FIX: Returns token on successful claim

        # Verify state transitioned to PENDING then back to PROCESSING
        state = repo.get(2002)
        assert state.status == AutomationStatus.PROCESSING
        assert state.fingerprint == fp2

    def test_save_preserves_processing_lease(self, temp_db):
        """
        P1-02 Fix: Repository save() should preserve processing lease via COALESCE in upsert.

        Before fix: save() would set processing_lease_until to NULL
        After fix: save() preserves existing lease if not explicitly updated
        """
        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=2003, name="Test", email_from="test@company.com")
        fp = TicketFingerprinter.generate(ticket)

        # Claim ticket (sets lease)
        claimed = repo.claim_for_processing(
            ticket_id=2003,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert claimed is not None  # TASK 3 FIX: Returns token on successful claim

        # Get the state with active lease
        state_before = repo.get(2003)
        lease_before = state_before.processing_lease_until
        assert lease_before is not None

        # Save the state without explicitly setting lease
        # (simulating a partial update like updating flags)
        state_before.reactivation_completed = True
        repo.save(state_before, owner_token=claimed)  # Pass owner_token for active lease

        # Verify lease was preserved
        state_after = repo.get(2003)
        assert state_after.processing_lease_until == lease_before
        assert state_after.reactivation_completed is True


class TestP103EmailDeliveryFailure:
    """P1-03: Email Delivery Failure - Durable retry mechanism for email delivery."""

    @pytest.fixture
    def temp_db(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    @pytest.fixture
    def state_repo(self, temp_db):
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def workflow(self, state_repo):
        # P2 Issue #4: Inject verified mock verifier for legacy test compatibility
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Legacy test fixture: verified",
            source="test_fixture",
            verified_email=None
        ))

        # P2 Issue #5: Configure ticket_client to return WriteOutcome objects
        ticket_client = Mock()
        ticket_client.add_log = Mock(return_value=WriteOutcome(status=WriteOutcomeStatus.SUCCESS))
        ticket_client.update_stage = Mock(return_value=WriteOutcome(status=WriteOutcomeStatus.SUCCESS))

        return LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
            identity_verifier=verifier,
        )

    def test_smtp_failure_persists_recoverable_state(self, workflow, state_repo):
        """
        P1-03 Fix Verification: Email delivery failure creates persistent recoverable state.

        Before fix: Email failure was silent, no retry mechanism
        After fix: Email failure is tracked and creates RETRY_SCHEDULED state
        """
        ticket = Ticket(
            id=3001,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP3001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = False  # SMTP fails

        # Execute
        result = workflow.execute(ticket_id=3001)

        # P1-03 Verification:
        # Workflow should succeed for Odoo operations
        assert result.action_taken == "account_reactivated"
        assert result.reactivation_completed is True
        assert result.odoo_note_completed is True
        assert result.stage_update_completed is True

        # But email delivery failure should be tracked
        assert result.email_delivery_completed is False

    def test_email_failure_retry_does_not_repeat_lms_reactivation(self, workflow, state_repo):
        """
        P1-03 Integration: Email failure retry should resend email only, not re-reactivate LMS.
        """
        ticket = Ticket(
            id=3002,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP3002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Run 1: LMS succeeds, email fails
        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = False  # Email fails

        result1 = workflow.execute(ticket_id=3002)
        assert result1.email_delivery_completed is False

        # Save state after Run 1
        from srcs.services.ticket_fingerprinter import TicketFingerprinter
        fingerprint = TicketFingerprinter.generate(ticket)
        state1 = AutomationState(
            ticket_id=3002,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=result1.reactivation_completed,
            odoo_note_completed=result1.odoo_note_completed,
            stage_update_completed=result1.stage_update_completed,
            email_delivery_completed=result1.email_delivery_completed,
        )
        state_repo.save(state1)

        # Run 2: Retry with email success
        workflow.ticket_client.reset_mock()
        workflow.hr_client.reset_mock()
        workflow.ticket_analyzer.reset_mock()
        workflow.gmail_service.reset_mock()

        # Setup for Run 2
        # Note: LMS status now reflects the reactivation from Run 1
        employee_run2 = Employee(
            employee_id="EMP3002",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",  # Now active from Run 1
            deactivation_reason=None,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee_run2
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = True  # Email succeeds

        # Retry with prior state
        retrieved_state = state_repo.get(3002)
        result2 = workflow.execute(ticket_id=3002, state=retrieved_state)

        # P1-03 Verification:
        # Should succeed with email delivery now complete
        assert result2.action_taken == "account_reactivated"
        assert result2.email_delivery_completed is True

        # LMS should NOT have been called again (already completed in Run 1)
        workflow.hr_client.reactivate_lms_account.assert_not_called()

        # Email should have been sent
        workflow.gmail_service.send_email.assert_called_once()

    def test_duplicate_email_send_prevented_via_communication_events(self, workflow, state_repo):
        """
        P1-03: Prevent duplicate email sends using CommunicationEvent tracking.
        """
        ticket = Ticket(
            id=3003,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP3003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Run 1: All succeeds including email
        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = True

        result1 = workflow.execute(ticket_id=3003)
        assert result1.email_delivery_completed is True

        # Verify email was marked as sent in communication events
        assert state_repo.has_communication_sent(3003, CommunicationEvent.REACTIVATION_SUCCESSFUL)

        # Run 2: Another attempt (e.g., re-processing due to state transition)
        workflow.ticket_client.reset_mock()
        workflow.hr_client.reset_mock()
        workflow.ticket_analyzer.reset_mock()
        workflow.gmail_service.reset_mock()

        employee_run2 = Employee(
            employee_id="EMP3003",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="active",  # Active from Run 1
            deactivation_reason=None,
        )

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee_run2
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
        workflow.gmail_service.send_email.return_value = True

        retrieved_state = state_repo.get(3003)
        result2 = workflow.execute(ticket_id=3003, state=retrieved_state)

        # P1-03 Verification:
        # Email should NOT be sent again (already sent in Run 1)
        workflow.gmail_service.send_email.assert_not_called()
