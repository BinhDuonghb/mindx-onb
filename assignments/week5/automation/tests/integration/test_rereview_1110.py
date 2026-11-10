"""Targeted Week 5 mentor re-review regressions (offline only)."""
import sqlite3
from unittest.mock import Mock

import pytest

from srcs.models import (
    AutomationState, AutomationStatus, DeactivationReason, Employee,
    EmployeeStatus, Ticket,
)
from srcs.services.decision_service import Decision, DecisionService
from srcs.services.identity_verifier import (
    IdentityVerifier, VerificationResult, VerificationStatus,
)
from srcs.services.login_workflow import LoginWorkflow, WorkflowResult
from srcs.services.ticket_analyzer import AnalysisResult, IssueType
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus
from srcs.repositories.automation_state_repository import AutomationStateRepository


def _employee(lms="active"):
    return Employee(
        employee_id="E77", name="Training User", email="user@example.com",
        status=EmployeeStatus.ACTIVE, lms_account_status=lms,
        deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS if lms == "deactivated" else None,
    )


def _ticket():
    return Ticket(id=77, name="Cannot login", email_from="user@example.com",
                  is_login_issue=True, issue_type=IssueType.CANNOT_LOGIN)


def _verifier(status):
    verifier = Mock(spec=IdentityVerifier)
    verifier.verify.return_value = VerificationResult(
        status=status, reason="simulated verification", source="test_fixture",
        verified_email="user@example.com" if status == VerificationStatus.VERIFIED else None,
    )
    return verifier


@pytest.mark.parametrize("status", [AutomationStatus.MANUAL_REVIEW, AutomationStatus.RETRY_SCHEDULED])
def test_active_lms_without_authorization_cannot_resume(status):
    verifier = _verifier(VerificationStatus.UNAVAILABLE)
    state = AutomationState(
        ticket_id=77, fingerprint="fp", status=status, reactivation_completed=False,
        odoo_note_completed=False, stage_update_completed=False,
        email_delivery_completed=False,
    )
    decision = DecisionService(verifier).decide(_employee(), _ticket(), state)
    assert decision.action == Decision.MANUAL_REVIEW
    assert "authorization" not in decision.reason.lower() or "approval" in decision.reason.lower()


def test_no_approval_cannot_reactivate_or_change_stage(tmp_path):
    state = AutomationState(ticket_id=77, fingerprint="fp", status=AutomationStatus.RETRY_SCHEDULED,
                            reactivation_completed=False, stage_update_completed=False)
    verifier = _verifier(VerificationStatus.UNAVAILABLE)
    ticket_client = Mock()
    ticket_client.get_ticket.return_value = _ticket()
    ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
    hr = Mock()
    hr.get_employee_by_email.return_value = _employee()
    analyzer = Mock()
    analyzer.analyze.return_value = AnalysisResult(
        is_login_issue=True, issue_type=IssueType.CANNOT_LOGIN,
        reason="login", confidence=0.95,
    )
    workflow = LoginWorkflow(ticket_client, hr, analyzer, gmail_service=None,
                             state_repo=AutomationStateRepository(tmp_path / "state.db"),
                             identity_verifier=verifier)
    result = workflow.execute(ticket_id=77, state=state)
    assert result.action_taken == "escalated_manual_review"
    assert result.reactivation_authorized is False
    hr.reactivate_lms_account.assert_not_called()
    ticket_client.update_stage.assert_not_called()


def test_verified_approval_proof_survives_sqlite_restart(tmp_path):
    path = tmp_path / "state.db"
    repo = AutomationStateRepository(path)
    state = AutomationState(ticket_id=77, fingerprint="fp", status=AutomationStatus.RETRY_SCHEDULED,
                            reactivation_authorized=True, reactivation_completed=True,
                            odoo_note_completed=True, stage_update_completed=True,
                            email_delivery_completed=False)
    assert repo.save(state)
    loaded = AutomationStateRepository(path).get(77)
    assert loaded.reactivation_authorized is True
    assert loaded.reactivation_completed is True
    assert DecisionService(_verifier(VerificationStatus.UNAVAILABLE)).decide(
        _employee(), _ticket(), loaded,
    ).action == Decision.APPROVE_REACTIVATION


def test_unapproved_state_fails_closed_after_sqlite_restart(tmp_path):
    path = tmp_path / "state.db"
    repo = AutomationStateRepository(path)
    assert repo.save(AutomationState(
        ticket_id=77, fingerprint="fp", status=AutomationStatus.RETRY_SCHEDULED,
        reactivation_completed=True, reactivation_authorized=False,
        email_delivery_completed=False,
    ))
    loaded = AutomationStateRepository(path).get(77)
    assert DecisionService(_verifier(VerificationStatus.UNAVAILABLE)).decide(
        _employee(), _ticket(), loaded,
    ).action == Decision.MANUAL_REVIEW


def test_email_missing_smtp_is_not_delivered(tmp_path):
    workflow = LoginWorkflow(Mock(), Mock(), Mock(), gmail_service=None,
                             state_repo=AutomationStateRepository(tmp_path / "s.db"))
    outcome = WorkflowResult(success=True, action_taken="account_reactivated", message="OK")
    assert workflow._send_outcome_email(_ticket(), _employee(), outcome) is False
    assert workflow._send_outcome_email(_ticket(), _employee(),
        WorkflowResult(success=True, action_taken="skipped", message="skip")) is False


def test_smtp_returns_false_is_not_delivered(tmp_path):
    gmail = Mock()
    gmail.send_email.return_value = False
    workflow = LoginWorkflow(Mock(), Mock(), Mock(), gmail_service=gmail,
                             state_repo=AutomationStateRepository(tmp_path / "s.db"))
    assert workflow._send_outcome_email(
        _ticket(), _employee(),
        WorkflowResult(success=True, action_taken="account_reactivated", message="OK"),
    ) is False
    gmail.send_email.assert_called_once()


def test_stage_done_guard_prevents_stage_write(tmp_path, monkeypatch):
    from srcs import config
    monkeypatch.setattr(config, "ODOO_STAGE_MAPPING", {"awaiting_confirmation": 4})
    monkeypatch.setattr(config, "ODOO_STAGE_DONE_IDS", frozenset({4}))
    ticket_client = Mock()
    ticket_client.get_ticket.return_value = _ticket()
    ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)
    hr = Mock()
    hr.get_employee_by_email.return_value = _employee("deactivated")
    hr.reactivate_lms_account.return_value = True
    analyzer = Mock()
    analyzer.analyze.return_value = AnalysisResult(is_login_issue=True,
        issue_type=IssueType.CANNOT_LOGIN, reason="login", confidence=0.95)
    workflow = LoginWorkflow(ticket_client, hr, analyzer, gmail_service=None,
        state_repo=AutomationStateRepository(tmp_path / "state.db"),
        identity_verifier=_verifier(VerificationStatus.VERIFIED))
    result = workflow.execute(77)
    assert result.action_taken == "retry_scheduled"
    assert result.reactivation_authorized is True
    assert result.stage_update_completed is False
    ticket_client.update_stage.assert_not_called()


def test_prior_manual_review_stays_unapproved_even_with_flags():
    state = AutomationState(ticket_id=77, fingerprint="fp", status=AutomationStatus.MANUAL_REVIEW,
        reactivation_authorized=True, reactivation_completed=True,
        email_delivery_completed=False)
    assert DecisionService(_verifier(VerificationStatus.UNAVAILABLE)).decide(
        _employee(), _ticket(), state).action == Decision.MANUAL_REVIEW


def test_training_string_does_not_bypass_runtime_identity_verification():
    # Success-path demo must inject an explicit VERIFIED fake verifier;
    # merely selecting a string must never authorize a real Odoo runner.
    result = IdentityVerifier("training").verify("user@example.com", "user@example.com")
    assert result.status == VerificationStatus.UNAVAILABLE


def test_legacy_sqlite_migration_defaults_prior_authorization_to_false(tmp_path):
    path = tmp_path / "legacy.db"
    repo = AutomationStateRepository(path)
    assert repo.save(AutomationState(
        ticket_id=77, fingerprint="fp", status=AutomationStatus.RETRY_SCHEDULED,
        reactivation_completed=True, reactivation_authorized=True,
    ))
    with sqlite3.connect(path) as conn:
        # Simulate a legacy database by rebuilding its table without the new column.
        conn.execute("ALTER TABLE automation_state RENAME TO old_state")
        conn.execute("CREATE TABLE automation_state AS SELECT ticket_id, fingerprint, status, last_decision, "
                     "last_reason, created_at, updated_at, last_checked_at, retry_count, next_retry_at, "
                     "last_error, reactivation_completed, odoo_note_completed, customer_response_completed, "
                     "stage_update_completed, email_delivery_completed, processing_lease_until, lease_owner_token, "
                     "ambiguous_write_outcome, ambiguous_write_context FROM old_state")
        conn.execute("DROP TABLE old_state")
    migrated = AutomationStateRepository(path)
    assert migrated.get(77).reactivation_authorized is False
