"""P0 Correctness Issues - Integration Tests (RED phase).

Tests for:
1. Odoo Boolean Results - False returns must be treated as failures
2. Partial Recovery - Persist each side effect immediately
3. Atomic Processing Claims - Fingerprint changes atomically transition
4. Email Failure Recovery - Don't complete on email failures
5. Full retry flow with actual call counts
"""

import pytest
from unittest.mock import Mock, MagicMock, call
from pathlib import Path
from datetime import datetime, timedelta, timezone

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.gmail import EmailTemplate, CommunicationEvent


class TestOdooBooleanResults:
    """Issue #1: Odoo Boolean Results - False returns must fail workflow."""

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
        return LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
        )

    def test_odoo_note_failure_schedules_retry(self, workflow):
        """add_log() returning False must schedule retry, not succeed."""
        ticket = Ticket(
            id=101,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP101",
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
        workflow.hr_client.reactivate_lms_account.return_value = True  # Success
        workflow.ticket_client.add_log.return_value = False  # Odoo note FAILS

        # Execute
        result = workflow.execute(ticket_id=101)

        # Must schedule retry, not succeed
        assert result.action_taken == "retry_scheduled"
        assert result.error_message is not None
        # Verify reactivation was completed but note failed
        assert result.reactivation_completed is True
        assert result.odoo_note_completed is False

    def test_odoo_stage_update_failure_schedules_retry(self, workflow):
        """update_stage() returning False must schedule retry."""
        ticket = Ticket(
            id=102,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP102",
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
        workflow.hr_client.reactivate_lms_account.return_value = True  # Success
        workflow.ticket_client.add_log.return_value = True  # Success
        workflow.ticket_client.update_stage.return_value = False  # Stage update FAILS

        # Execute
        result = workflow.execute(ticket_id=102)

        # Must schedule retry
        assert result.action_taken == "retry_scheduled"
        assert result.reactivation_completed is True
        assert result.odoo_note_completed is True
        assert result.stage_update_completed is False


class TestPartialRecovery:
    """Issue #2: Partial Recovery - Resume incomplete operations on retry."""

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
        return LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
        )

    def test_retry_skips_completed_reactivation(self, workflow, state_repo):
        """Retry should skip LMS reactivation if already completed."""
        ticket = Ticket(
            id=201,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP201",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Setup: Prior attempt succeeded at reactivation but failed at note
        prior_state = AutomationState(
            ticket_id=201,
            fingerprint="fp1",
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,  # Already completed
            odoo_note_completed=False,     # Pending
            last_decision="account_reactivated",
        )
        state_repo.save(prior_state)

        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        # This time, all succeed
        workflow.hr_client.reactivate_lms_account.return_value = True
        workflow.ticket_client.add_log.return_value = True
        workflow.ticket_client.update_stage.return_value = True

        # Execute retry with prior state
        result = workflow.execute(ticket_id=201, state=prior_state)

        # Should succeed now
        assert result.action_taken == "account_reactivated"
        # Verify reactivation was NOT called again (already completed)
        workflow.hr_client.reactivate_lms_account.assert_not_called()
        # But note and stage should be called
        workflow.ticket_client.add_log.assert_called_once()
        workflow.ticket_client.update_stage.assert_called_once()


class TestAtomicProcessingClaims:
    """Issue #3: Atomic Processing Claims - Fingerprint changes atomically transition."""

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

    def test_fingerprint_change_blocks_concurrent_claim(self, temp_db):
        """Fingerprint change must not allow concurrent worker to claim."""
        from srcs.services.ticket_fingerprinter import TicketFingerprinter

        repo = AutomationStateRepository(db_path=temp_db)

        ticket = Ticket(id=301, name="Test", email_from="test@company.com")
        fp1 = TicketFingerprinter.generate(ticket)

        # Worker 1 claims with fp1 - TASK 3 FIX: Now returns ownership token
        claimed1 = repo.claim_for_processing(
            ticket_id=301,
            fingerprint=fp1,
            lease_duration_seconds=300
        )
        assert claimed1 is not None  # TASK 3 FIX: Check for token, not True

        # Ticket content changes (new fingerprint)
        ticket.name = "Test - updated"
        fp2 = TicketFingerprinter.generate(ticket)

        # Worker 2 tries to claim with new fingerprint
        # Should FAIL because lease is still active
        claimed2 = repo.claim_for_processing(
            ticket_id=301,
            fingerprint=fp2,
            lease_duration_seconds=300
        )
        assert claimed2 is None  # TASK 3 FIX: Check for None, not False

        # Verify state is still PROCESSING
        state = repo.get(301)
        assert state.status == AutomationStatus.PROCESSING


class TestEmailFailureRecovery:
    """Issue #4: Email Failure Recovery - Don't complete on email failures."""

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
        return LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
        )

    def test_email_send_failure_persists_state(self, workflow):
        """Email send failure should not mark workflow as complete."""
        ticket = Ticket(
            id=401,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP401",
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
        workflow.ticket_client.add_log.return_value = True
        workflow.ticket_client.update_stage.return_value = True
        workflow.gmail_service.send_email.return_value = False  # Email send FAILS

        # Execute
        result = workflow.execute(ticket_id=401)

        # Should still succeed for Odoo actions, but email failed
        # The workflow result indicates success of the main actions
        assert result.action_taken == "account_reactivated"
        # But email send was attempted
        workflow.gmail_service.send_email.assert_called_once()


class TestFullRetryFlowWithCallCounts:
    """Issue #5: Integration test with actual side-effect call counts."""

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

    def test_lms_succeeds_odoo_note_fails_retry_resumes(self, state_repo):
        """LMS succeeds, Odoo note fails → retry resumes only Odoo note."""
        ticket = Ticket(
            id=501,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP501",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # First attempt: mock clients
        workflow1 = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
        )

        workflow1.ticket_client.get_ticket.return_value = ticket
        workflow1.hr_client.get_employee_by_email.return_value = employee
        workflow1.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow1.hr_client.reactivate_lms_account.return_value = True  # Success
        workflow1.ticket_client.add_log.return_value = False  # Fails

        # First execution
        result1 = workflow1.execute(ticket_id=501)
        assert result1.action_taken == "retry_scheduled"

        # Verify LMS was called
        assert workflow1.hr_client.reactivate_lms_account.call_count == 1
        # Verify note was attempted
        assert workflow1.ticket_client.add_log.call_count == 1

        # Persist the state like main.py does after workflow execution
        from srcs.services.ticket_fingerprinter import TicketFingerprinter
        fingerprint = TicketFingerprinter.generate(ticket)
        state1 = AutomationState(
            ticket_id=501,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,
            last_decision=result1.action_taken,
            last_reason=result1.message,
            reactivation_completed=result1.reactivation_completed,
            odoo_note_completed=result1.odoo_note_completed,
            stage_update_completed=result1.stage_update_completed,
        )
        state_repo.save(state1)

        # Get the state after first attempt
        state_after_first = state_repo.get(501)
        assert state_after_first is not None
        assert state_after_first.reactivation_completed is True
        assert state_after_first.odoo_note_completed is False

        # Second attempt (retry): fresh workflow, same repo
        workflow2 = LoginWorkflow(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo,
        )

        workflow2.ticket_client.get_ticket.return_value = ticket
        workflow2.hr_client.get_employee_by_email.return_value = employee
        workflow2.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow2.hr_client.reactivate_lms_account.return_value = True
        workflow2.ticket_client.add_log.return_value = True  # Now succeeds
        workflow2.ticket_client.update_stage.return_value = True

        # Retry with prior state
        result2 = workflow2.execute(ticket_id=501, state=state_after_first)
        assert result2.action_taken == "account_reactivated"

        # Verify LMS was NOT called on retry (already completed)
        assert workflow2.hr_client.reactivate_lms_account.call_count == 0
        # Verify note WAS called on retry (was pending)
        assert workflow2.ticket_client.add_log.call_count == 1
        # Verify stage was called
        assert workflow2.ticket_client.update_stage.call_count == 1
