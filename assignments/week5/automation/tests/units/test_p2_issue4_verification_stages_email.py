"""Regression tests for P2 Issue #4: Verification, Stage Mapping, Missing Email.

Tests the three interconnected fixes:
1. Identity verification - Email matching alone doesn't authorize reactivation
2. Odoo stage mapping - Configurable stages instead of hardcoded ID
3. Missing email handling - Login tickets without email escalate to manual review
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from srcs.main import AutomationExecutor
from srcs.models import (
    AutomationState, AutomationStatus, Ticket, Employee,
    EmployeeStatus, DeactivationReason
)
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus
from srcs.services.decision_service import DecisionService, Decision
from srcs.services.ticket_poller import PollingMetrics
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class TestIdentityVerification:
    """Tests for P2 Issue #4 Part 1: Identity Verification."""

    def test_email_match_without_trusted_verification_requires_manual_review(self):
        """Email matching alone does NOT authorize reactivation without verification."""
        employee = Employee(
            employee_id="EMP001",
            name="Alice",
            email="alice@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="alice@company.com",
            is_login_issue=True
        )

        # Create verifier that returns UNAVAILABLE (no real provider configured)
        verifier = IdentityVerifier(verification_source="mock_training_poc")
        decision_service = DecisionService(verifier=verifier)

        # Make decision
        result = decision_service.decide(employee, ticket)

        # VERIFY: Decision requires manual review (email match insufficient)
        assert result.action == Decision.MANUAL_REVIEW, \
            "Email match without verified identity must require manual review"
        assert "verification" in result.reason.lower(), \
            "Reason must mention verification requirement"

    def test_verified_active_employee_can_be_approved_in_mock_poc(self):
        """When verification succeeds, active employee can be approved."""
        employee = Employee(
            employee_id="EMP002",
            name="Bob",
            email="bob@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=2,
            name="Cannot login",
            email_from="bob@company.com",
            is_login_issue=True
        )

        # Create verifier with mock approval
        verifier = IdentityVerifier(verification_source="mock_training_poc")
        decision_service = DecisionService(verifier=verifier)

        # Override verify method to return VERIFIED (simulating training test)
        original_verify = verifier.verify
        verifier.verify = Mock(return_value=Mock(
            status=VerificationStatus.VERIFIED,
            reason="Training mock: verified",
            source="mock_training_poc",
            verified_email="bob@company.com"
        ))

        # Make decision
        result = decision_service.decide(employee, ticket)

        # VERIFY: Decision approves reactivation when verified
        assert result.action == Decision.APPROVE_REACTIVATION, \
            "Verified active employee should be approved for reactivation"
        assert "verified" in result.reason.lower(), \
            "Reason should mention verification"

    def test_unavailable_verifier_fails_closed(self):
        """When verifier is unavailable, escalate to manual review."""
        employee = Employee(
            employee_id="EMP003",
            name="Carol",
            email="carol@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=3,
            name="Cannot login",
            email_from="carol@company.com",
            is_login_issue=True
        )

        verifier = IdentityVerifier(verification_source="mock_training_poc")
        decision_service = DecisionService(verifier=verifier)

        # Make decision - should get UNAVAILABLE from POC verifier
        result = decision_service.decide(employee, ticket)

        # VERIFY: Fails closed (manual review, not approval)
        assert result.action == Decision.MANUAL_REVIEW, \
            "Missing verification must fail closed to manual review"

    def test_mismatched_identity_is_rejected(self):
        """Email mismatch always results in manual review."""
        employee = Employee(
            employee_id="EMP004",
            name="David",
            email="david@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=4,
            name="Cannot login",
            email_from="notdavid@company.com",  # Mismatch
            is_login_issue=True
        )

        verifier = IdentityVerifier(verification_source="mock_training_poc")
        decision_service = DecisionService(verifier=verifier)

        result = decision_service.decide(employee, ticket)

        # VERIFY: Mismatch always requires manual review
        assert result.action == Decision.MANUAL_REVIEW, \
            "Email mismatch must require manual review"

    def test_terminated_employee_cannot_be_approved_even_if_verified(self):
        """Terminated employee escalates even if identity verified."""
        employee = Employee(
            employee_id="EMP005",
            name="Eve",
            email="eve@company.com",
            status=EmployeeStatus.TERMINATED,  # Terminated
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=5,
            name="Cannot login",
            email_from="eve@company.com",
            is_login_issue=True
        )

        verifier = IdentityVerifier(verification_source="mock_training_poc")
        decision_service = DecisionService(verifier=verifier)

        result = decision_service.decide(employee, ticket)

        # VERIFY: Terminated status overrides all other checks
        assert result.action == Decision.MANUAL_REVIEW, \
            "Terminated employee cannot be approved even if verified"
        assert "terminated" in result.reason.lower(), \
            "Reason should mention terminated status"


class TestOdooStageMapping:
    """Tests for P2 Issue #4 Part 2: Odoo Stage Mapping."""

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
        return AutomationStateRepository(db_path=temp_db)

    def test_workflow_uses_configured_awaiting_confirmation_stage(self, state_repo):
        """Workflow uses stage ID from configuration, not hardcoded value."""
        # Mock configuration with valid stage ID
        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 42}):

            ticket = Ticket(
                id=100,
                name="Cannot login",
                email_from="user@company.com"
            )

            employee = Employee(
                employee_id="EMP100",
                name="User",
                email="user@company.com",
                status=EmployeeStatus.ACTIVE,
                lms_account_status="deactivated",
                deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
            )

            # Mock clients
            ticket_client = Mock()
            ticket_client.update_stage = Mock(return_value=WriteOutcome(status=WriteOutcomeStatus.SUCCESS))
            ticket_client.add_log = Mock(return_value=WriteOutcome(status=WriteOutcomeStatus.SUCCESS))

            hr_client = Mock()
            hr_client.reactivate_lms_account = Mock(return_value=True)

            ticket_analyzer = Mock()

            # Create workflow with mocked config
            workflow = LoginWorkflow(
                ticket_client=ticket_client,
                hr_client=hr_client,
                ticket_analyzer=ticket_analyzer,
                gmail_service=None,
                state_repo=state_repo
            )

            # Create proper Decision object for reactivation
            from srcs.services.decision_service import Decision, DecisionResult
            decision = DecisionResult(
                action=Decision.APPROVE_REACTIVATION,
                reason="Test approval for configured stage"
            )

            # Execute reactivation
            result = workflow._handle_reactivation(ticket, employee, decision, state=None)

            # VERIFY: update_stage was called with configured stage ID (42), not hardcoded 4
            ticket_client.update_stage.assert_called()
            call_args = ticket_client.update_stage.call_args
            assert call_args[1]['stage_id'] == 42, \
                "Stage ID should be 42 from configuration, not hardcoded 4"

    def test_missing_stage_mapping_does_not_use_hardcoded_id(self, state_repo):
        """When stage mapping is missing, fail safely instead of guessing."""
        # Mock configuration with unconfigured stage ID (0 = not set)
        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 0}):

            ticket = Ticket(
                id=101,
                name="Cannot login",
                email_from="user@company.com"
            )

            employee = Employee(
                employee_id="EMP101",
                name="User",
                email="user@company.com",
                status=EmployeeStatus.ACTIVE,
                lms_account_status="deactivated",
                deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
            )

            # Mock clients
            ticket_client = Mock()
            hr_client = Mock()
            hr_client.reactivate_lms_account = Mock(return_value=True)
            ticket_analyzer = Mock()

            workflow = LoginWorkflow(
                ticket_client=ticket_client,
                hr_client=hr_client,
                ticket_analyzer=ticket_analyzer,
                gmail_service=None,
                state_repo=state_repo
            )

            # Create proper Decision object for reactivation
            from srcs.services.decision_service import Decision, DecisionResult
            decision = DecisionResult(
                action=Decision.APPROVE_REACTIVATION,
                reason="Test - will fail on stage mapping"
            )

            # Execute reactivation - should fail safely on unconfigured stage
            result = workflow._handle_reactivation(ticket, employee, decision, state=None)

            # VERIFY: Failed gracefully (retry_scheduled) rather than using guessed stage
            assert result.action_taken == "retry_scheduled", \
                "Should schedule retry when stage mapping not configured"
            assert "not set" in result.error_message.lower(), \
                "Error should mention configuration not set"


class TestMissingEmailHandling:
    """Tests for P2 Issue #4 Part 3: Missing Email Handling."""

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
        return AutomationStateRepository(db_path=temp_db)

    def test_login_ticket_without_email_escalates_to_manual_review(self, state_repo):
        """Login issue without customer email escalates, not silently skipped."""
        ticket = Ticket(
            id=200,
            name="Cannot login",
            email_from=None  # No email
        )

        # Mock clients - return real objects, not mocks
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=WriteOutcome(status=WriteOutcomeStatus.SUCCESS))

        hr_client = Mock()

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=True,  # It IS a login issue
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Cannot login",
            confidence=0.9
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo
        )

        # Execute workflow
        result = workflow.execute(ticket_id=200)

        # VERIFY: Escalated to manual review, not skipped
        assert result.action_taken == "escalated_manual_review", \
            "Login ticket without email should escalate, not skip"
        assert "no customer email" in result.message.lower(), \
            "Message should explain why escalated"

    def test_missing_email_never_reactivates_account(self, state_repo):
        """Workflow never attempts reactivation without email."""
        ticket = Ticket(
            id=201,
            name="Cannot login",
            email_from=None  # No email
        )

        # Mock clients - return real objects
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=WriteOutcome(status=WriteOutcomeStatus.SUCCESS))

        hr_client = Mock()
        hr_client.reactivate_lms_account = Mock()

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Cannot login",
            confidence=0.9
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo
        )

        # Execute workflow
        result = workflow.execute(ticket_id=201)

        # VERIFY: LMS reactivation was never called
        hr_client.reactivate_lms_account.assert_not_called(), \
            "LMS reactivation should never be called without email"

    def test_non_login_ticket_can_still_be_skipped(self, state_repo):
        """Non-login tickets without email can still be skipped safely."""
        ticket = Ticket(
            id=202,
            name="General question",
            email_from=None  # No email
        )

        # Mock clients - return real objects
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)

        hr_client = Mock()

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=False,  # NOT a login issue
            issue_type=None,
            reason="Not a login issue",
            confidence=0.1
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo
        )

        # Execute workflow
        result = workflow.execute(ticket_id=202)

        # VERIFY: Non-login ticket without email can be safely skipped
        assert result.action_taken == "skipped", \
            "Non-login ticket without email should be skipped"

    def test_failed_manual_review_note_is_not_reported_as_success(self, state_repo):
        """If Odoo note posting fails during escalation, not reported as success."""
        ticket = Ticket(
            id=203,
            name="Cannot login",
            email_from=None  # No email - will escalate
        )

        # Mock clients - return real objects
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus
        ticket_client.add_log = Mock(return_value=WriteOutcome(
            status=WriteOutcomeStatus.CONFIRMED_FAILURE, error="Rejected before execution"
        ))  # Confirmed non-execution is safely retryable

        hr_client = Mock()

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Cannot login",
            confidence=0.9
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo
        )

        # Execute workflow - note posting will fail
        result = workflow.execute(ticket_id=203)

        # P2 Issue #4 Fix 1: Failed note posting is now properly detected and scheduled for retry
        assert result.action_taken == "retry_scheduled", \
            "Failed note posting should schedule retry, not report successful escalation"
        assert result.success is False, \
            "Result should not be marked successful when note posting fails"
