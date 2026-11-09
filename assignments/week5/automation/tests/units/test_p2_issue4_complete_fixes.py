"""Complete P2 Issue #4 fixes: Missing email escalation, legacy fixture updates, and stage mapping.

Tests for:
1. Missing email escalation with Odoo note posting and failure handling
2. Legacy test fixture injection for authorized reactivation paths
3. Workflow-level stage mapping and escalation safety tests
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from srcs.models import (
    AutomationState, AutomationStatus, Ticket, Employee,
    EmployeeStatus, DeactivationReason
)
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult


class TestMissingEmailEscalation:
    """P2 Issue #4 Fix 1: Missing email escalation with proper Odoo note handling."""

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

    def test_missing_email_posts_manual_review_note(self, state_repo):
        """Missing email login ticket posts clear Odoo note explaining escalation."""
        ticket = Ticket(
            id=300,
            name="Cannot login",
            email_from=None  # No email
        )

        # Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=True)  # Success

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

        # Execute workflow
        result = workflow.execute(ticket_id=300)

        # VERIFY: Odoo note was posted
        ticket_client.add_log.assert_called()
        call_args = ticket_client.add_log.call_args
        assert "no customer email" in call_args[1]['log_message'].lower(), \
            "Note should explain why email is required"

        # VERIFY: Escalation was reported as successful
        assert result.action_taken == "escalated_manual_review"
        assert result.odoo_note_completed is True

    def test_missing_email_note_failure_is_retryable(self, state_repo):
        """When Odoo note posting fails, escalation is marked retryable, not completed."""
        ticket = Ticket(
            id=301,
            name="Cannot login",
            email_from=None
        )

        # Mock clients - note posting fails
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=False)  # Failure

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

        # Execute workflow
        result = workflow.execute(ticket_id=301)

        # VERIFY: Failure was reported as retryable, not successful
        assert result.action_taken == "retry_scheduled", \
            "Failed note posting should schedule retry"
        assert result.success is False, \
            "Result should not be marked successful"
        assert "failed" in result.error_message.lower(), \
            "Error should mention note posting failure"

    def test_missing_email_never_reactivates(self, state_repo):
        """Missing email ticket never attempts HR lookup or LMS reactivation."""
        ticket = Ticket(
            id=302,
            name="Cannot login",
            email_from=None
        )

        # Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=True)

        hr_client = Mock()
        hr_client.get_employee_by_email = Mock()  # Should not be called
        hr_client.reactivate_lms_account = Mock()  # Should not be called

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
        result = workflow.execute(ticket_id=302)

        # VERIFY: No HR or LMS operations attempted
        hr_client.get_employee_by_email.assert_not_called(), \
            "Should not lookup employee without email"
        hr_client.reactivate_lms_account.assert_not_called(), \
            "Should not reactivate LMS without email"


class TestLegacyFixtureInjection:
    """P2 Issue #4 Fix 2: Update legacy tests with explicit verified identity fixtures."""

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

    def test_verified_mock_identity_allows_reactivation(self, state_repo):
        """With explicitly verified mock identity, active employee is approved for reactivation."""
        employee = Employee(
            employee_id="EMP400",
            name="Test Employee",
            email="test@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=400,
            name="Cannot login",
            email_from="test@company.com"
        )

        # Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=True)
        ticket_client.update_stage = Mock(return_value=True)

        hr_client = Mock()
        hr_client.get_employee_by_email = Mock(return_value=employee)
        hr_client.reactivate_lms_account = Mock(return_value=True)

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Cannot login",
            confidence=0.9
        ))

        # P2 Issue #4 Fix 2: Create verified mock verifier for legacy test
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Test fixture: explicitly verified",
            source="test_fixture",
            verified_email="test@company.com"
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo,
            identity_verifier=verifier
        )

        # Mock config for stage mapping
        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
            # Execute workflow
            result = workflow.execute(ticket_id=400)

        # VERIFY: With verified identity, reactivation is approved
        assert result.action_taken == "account_reactivated", \
            "Verified active employee should be reactivated"
        assert hr_client.reactivate_lms_account.called, \
            "LMS reactivation should be attempted"

    def test_unavailable_identity_fails_closed_at_workflow_level(self, state_repo):
        """When identity verification unavailable, fail-closed to manual review."""
        employee = Employee(
            employee_id="EMP401",
            name="Test Employee",
            email="test@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=401,
            name="Cannot login",
            email_from="test@company.com"
        )

        # Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=True)

        hr_client = Mock()
        hr_client.get_employee_by_email = Mock(return_value=employee)
        hr_client.reactivate_lms_account = Mock()  # Should not be called

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Cannot login",
            confidence=0.9
        ))

        # Create verifier that returns UNAVAILABLE (default POC behavior)
        verifier = IdentityVerifier(verification_source="mock_training_poc")

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo,
            identity_verifier=verifier
        )

        # Execute workflow
        result = workflow.execute(ticket_id=401)

        # VERIFY: Fails closed to manual review when verification unavailable
        assert result.action_taken == "escalated_manual_review", \
            "Should escalate when verification unavailable"
        hr_client.reactivate_lms_account.assert_not_called(), \
            "Should not reactivate without verified identity"


class TestStageAndEscalationSafety:
    """P2 Issue #4 Fix 3: Workflow-level stage mapping and escalation safety tests."""

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

    def test_workflow_respects_configured_stage_in_reactivation(self, state_repo):
        """Workflow uses configured stage ID when posting reactivation."""
        employee = Employee(
            employee_id="EMP600",
            name="Stage Test",
            email="stage@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS
        )

        ticket = Ticket(
            id=600,
            name="Cannot login",
            email_from="stage@company.com"
        )

        # Mock clients
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=True)
        ticket_client.update_stage = Mock(return_value=True)

        hr_client = Mock()
        hr_client.get_employee_by_email = Mock(return_value=employee)
        hr_client.reactivate_lms_account = Mock(return_value=True)

        ticket_analyzer = Mock()
        ticket_analyzer.analyze = Mock(return_value=AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Cannot login",
            confidence=0.9
        ))

        # Verified verifier
        verifier = Mock(spec=IdentityVerifier)
        verifier.verify = Mock(return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason="Fixture verification",
            source="test",
            verified_email="stage@company.com"
        ))

        workflow = LoginWorkflow(
            ticket_client=ticket_client,
            hr_client=hr_client,
            ticket_analyzer=ticket_analyzer,
            gmail_service=None,
            state_repo=state_repo,
            identity_verifier=verifier
        )

        # Mock config with configured stage ID
        with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 99}):
            result = workflow.execute(ticket_id=600)

        # VERIFY: Reactivation completed and stage was updated with configured ID
        assert result.action_taken == "account_reactivated"
        ticket_client.update_stage.assert_called()
        call_args = ticket_client.update_stage.call_args
        assert call_args[1]['stage_id'] == 99, \
            "Workflow should use configured stage ID (99)"

    def test_escalation_posts_odoo_note_and_fails_safely_if_note_fails(self, state_repo):
        """Escalation properly posts Odoo note and marks retryable on failure."""
        employee = Employee(
            employee_id="EMP601",
            name="Escalation Test",
            email="escalate@company.com",
            status=EmployeeStatus.TERMINATED  # Will require manual review
        )

        ticket = Ticket(
            id=601,
            name="Cannot login",
            email_from="escalate@company.com"
        )

        # Mock clients - note posting will fail
        ticket_client = Mock()
        ticket_client.get_ticket = Mock(return_value=ticket)
        ticket_client.add_log = Mock(return_value=False)  # Failure

        hr_client = Mock()
        hr_client.get_employee_by_email = Mock(return_value=employee)

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
        result = workflow.execute(ticket_id=601)

        # VERIFY: Escalation was attempted but note posting failure prevented success
        assert result.action_taken == "retry_scheduled", \
            "Should schedule retry when note posting fails"
        assert result.success is False, \
            "Result should not be marked successful when note posting fails"
        ticket_client.add_log.assert_called(), \
            "Should attempt to post note for escalation"
