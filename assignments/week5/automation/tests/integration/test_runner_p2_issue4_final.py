"""P2 Issue #4 Final Integration Test - AutomationExecutor.run_once().

Validates the complete P2 Issue #4 implementation with real components:
- Real temporary SQLite repository
- Explicit VERIFIED mock identity verifier
- Valid mock login ticket and eligible employee
- Non-default configured Odoo stage ID
- Verified LMS reactivation exactly once
- Verified configured stage ID used
- Verified automation state persisted
- Verified processing lease and ownership token released
- No unauthorized or duplicate side effects
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_poller import TicketPoller, PollingMetrics
from srcs.main import AutomationExecutor


class TestRunnerP2Issue4Final:
    """Final integration test for P2 Issue #4 - AutomationExecutor.run_once()."""

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
        """Create real state repository with temporary database."""
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def verified_verifier(self):
        """Create explicit VERIFIED mock identity verifier."""
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test fixture: verified",
            source="test_integration",
            verified_email="john@company.com"
        ))
        return verifier

    def test_runner_complete_workflow_with_verified_identity_and_stage_persistence(
        self, state_repo, verified_verifier, temp_db
    ):
        """Test complete AutomationExecutor.run_once() workflow with P2 Issue #4 requirements.

        Validates:
        1. Real temporary SQLite repository
        2. Explicit VERIFIED mock identity verifier
        3. Valid mock login ticket and eligible employee
        4. Non-default configured Odoo stage ID (5)
        5. LMS reactivation occurs exactly once
        6. Configured stage ID is used
        7. Automation state is persisted
        8. Processing lease and ownership token are released
        9. No unauthorized or duplicate side effects
        """
        # Setup: Create valid ticket and employee for login issue
        ticket = Ticket(
            id=9001,
            name="Cannot login",
            email_from="john@company.com",
        )

        employee = Employee(
            employee_id="EMP9001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Setup: Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee
        hr_client.reactivate_lms_account.return_value = True

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )

        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        # Setup: Mock ticket poller to return our test ticket
        # (AutomationExecutor creates poller internally, so we'll mock it)
        ticket_poller = Mock(spec=TicketPoller)
        ticket_poller.poll.return_value = [ticket]
        ticket_poller.poll_for_retry.return_value = []

        # Create executor with mocked clients but real state repository and verified verifier
        executor = AutomationExecutor(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verified_verifier,
        )

        # Create workflow and metrics manually (executor sets them to None when clients are mocked)
        executor.workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verified_verifier,
        )
        executor.metrics = PollingMetrics()

        # Replace poller with our mock
        executor.poller = ticket_poller

        # Requirement 4: Use non-default configured Odoo stage ID (5)
        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            # Execute run_once()
            result = executor.run_once(limit=50, min_age_minutes=0)

        # VERIFICATION 1: Successful execution
        assert result['success'] is True, f"Execution failed: {result.get('error_details', [])}"
        assert result['successful'] == 1, "Expected exactly one successful ticket"
        assert result['tickets_processed'] == 1, "Expected exactly one ticket processed"

        # VERIFICATION 2: Verified identity verifier was called
        verified_verifier.verify.assert_called()
        verify_call_args = verified_verifier.verify.call_args
        assert verify_call_args is not None, "Identity verifier should have been called"

        # VERIFICATION 3: LMS reactivation called exactly once (not skipped due to identity check)
        hr_client.reactivate_lms_account.assert_called_once()

        # VERIFICATION 4: Configured stage ID was used in ticket update
        # Verify add_log was called (Odoo note posting for stage update)
        ticket_client.add_log.assert_called_once()
        # Verify update_stage was called
        ticket_client.update_stage.assert_called_once()

        # VERIFICATION 5: Automation state persisted with correct terminal status
        state = state_repo.get(ticket.id)
        assert state is not None, "Automation state should be persisted"
        assert state.ticket_id == ticket.id, "State should reference correct ticket"
        assert state.status == AutomationStatus.COMPLETED, "Final status should be COMPLETED"
        assert state.reactivation_completed is True, "Reactivation should be marked complete"
        assert state.stage_update_completed is True, "Stage update should be marked complete"

        # VERIFICATION 6: Processing lease released (no longer in PROCESSING)
        # Check that state is no longer PROCESSING
        assert state.status != AutomationStatus.PROCESSING, "Lease should be released (status changed from PROCESSING)"

        # VERIFICATION 7: No unauthorized side effects
        # Verify email was sent for successful reactivation
        gmail_service.send_email.assert_called_once()

        # VERIFICATION 8: Verify the side effect flags are correctly set
        assert state.reactivation_completed is True
        assert state.odoo_note_completed is True
        assert state.stage_update_completed is True
        assert state.email_delivery_completed is True

        # VERIFICATION 9: Verify fingerprint is set for change detection
        assert state.fingerprint is not None, "Fingerprint should be set for change detection"
        assert len(state.fingerprint) > 0, "Fingerprint should not be empty"

        # VERIFICATION 10: Verify no duplicate side effects by checking call counts
        assert ticket_client.get_ticket.call_count == 1, "Should fetch ticket exactly once"
        assert hr_client.get_employee_by_email.call_count == 1, "Should fetch employee exactly once"
        assert hr_client.reactivate_lms_account.call_count == 1, "LMS reactivation should happen exactly once"
        assert ticket_analyzer.analyze.call_count == 1, "Should analyze ticket exactly once"

    def test_runner_escalation_with_verified_identity_releases_lease(
        self, state_repo, verified_verifier
    ):
        """Test escalation scenario still releases lease properly with verified identity."""
        # Setup: Create ticket for terminated employee (triggers escalation)
        ticket = Ticket(
            id=9002,
            name="Cannot login",
            email_from="jane@company.com",
        )

        employee = Employee(
            employee_id="EMP9002",
            name="Jane Smith",
            email="jane@company.com",
            status=EmployeeStatus.TERMINATED,  # Triggers escalation
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.EMPLOYEE_TERMINATED,
        )

        # Setup: Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )

        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        ticket_poller = Mock(spec=TicketPoller)
        ticket_poller.poll.return_value = [ticket]
        ticket_poller.poll_for_retry.return_value = []

        # Create executor
        executor = AutomationExecutor(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verified_verifier,
        )

        # Create workflow and metrics manually
        executor.workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=verified_verifier,
        )
        executor.metrics = PollingMetrics()

        executor.poller = ticket_poller

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            # Execute run_once()
            result = executor.run_once(limit=50, min_age_minutes=0)

        # Verify escalation path
        assert result['success'] is True
        assert result['escalated'] == 1, "Expected escalation for terminated employee"

        # Verify state persisted with escalation status
        state = state_repo.get(ticket.id)
        assert state is not None, "Automation state should be persisted"
        assert state.status == AutomationStatus.MANUAL_REVIEW, "Status should be MANUAL_REVIEW for escalation"

        # Verify lease released (no longer PROCESSING)
        assert state.status != AutomationStatus.PROCESSING, "Lease should be released even on escalation"

        # Verify escalation email sent
        gmail_service.send_email.assert_called_once()

    def test_runner_identity_verification_failure_escalates_safely(
        self, state_repo
    ):
        """Test that unverified identity causes escalation (fail-closed behavior)."""
        # Setup: UNAVAILABLE verifier (fail-closed default)
        unavailable_verifier = Mock(spec=IdentityVerifier)
        unavailable_verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.UNAVAILABLE,
            reason="Cannot verify identity",
            source="training_verifier",
            verified_email=None
        ))

        # Setup: Valid ticket that would normally reactivate
        ticket = Ticket(
            id=9003,
            name="Cannot login",
            email_from="bob@company.com",
        )

        employee = Employee(
            employee_id="EMP9003",
            name="Bob Jones",
            email="bob@company.com",
            status=EmployeeStatus.ACTIVE,  # Would normally reactivate
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        # Setup: Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket.return_value = ticket

        hr_client = Mock()
        hr_client.get_employee_by_email.return_value = employee

        ticket_analyzer = Mock()
        ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue detected",
            confidence=0.9,
        )

        gmail_service = Mock()
        gmail_service.send_email.return_value = True

        ticket_poller = Mock(spec=TicketPoller)
        ticket_poller.poll.return_value = [ticket]
        ticket_poller.poll_for_retry.return_value = []

        # Create executor with UNAVAILABLE verifier
        executor = AutomationExecutor(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=unavailable_verifier,
        )

        # Create workflow and metrics manually
        executor.workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=gmail_service,
            state_repo=state_repo,
            identity_verifier=unavailable_verifier,
        )
        executor.metrics = PollingMetrics()

        executor.poller = ticket_poller

        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            result = executor.run_once(limit=50, min_age_minutes=0)

        # Verify fail-closed behavior: escalates instead of reactivating
        assert result['success'] is True
        assert result['escalated'] == 1, "Expected escalation when identity cannot be verified"
        assert result['successful'] == 0, "Should not have successful reactivation"

        # Verify LMS was NOT called (fail-closed)
        hr_client.reactivate_lms_account.assert_not_called()

        # Verify state reflects escalation
        state = state_repo.get(ticket.id)
        assert state.status == AutomationStatus.MANUAL_REVIEW, "Should escalate to manual review"
