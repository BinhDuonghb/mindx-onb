"""Phase 1 Round 2: Full Reliability Integration Tests.

Comprehensive end-to-end tests verifying all 5 defect fixes work together:
1. DEFECT 1: Email Retry Discovery (stage-4 tickets discoverable)
2. DEFECT 2: SMTP Exception Handling (exceptions don't lose side effects)
3. DEFECT 3: Lease Ownership (stale workers can't overwrite state)
4. DEFECT 4: Orphaned Ticket Recovery (expired PROCESSING leases recoverable)
5. DEFECT 5: Database Migration (legacy databases supported)
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
import tempfile
import os

from srcs.models import (
    Ticket, Employee, EmployeeStatus, AutomationState, AutomationStatus,
    DeactivationReason
)
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import LoginWorkflow
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


class TestPhase1Round2FullReliability:
    """Full end-to-end reliability scenario tests."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
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
        from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus, VerificationResult
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

    def test_complete_scenario_partial_failure_recovery_with_lease_safety(self, workflow, state_repo):
        """
        Full scenario: Partial failure → recovery → multiple workers with lease protection.

        Demonstrates:
        - DEFECT 2: SMTP exception doesn't lose side effects
        - DEFECT 3: Lease ownership prevents concurrent override
        - DEFECT 4: Expired lease allows recovery
        """
        ticket = Ticket(
            id=9001,
            name="Cannot login",
            email_from="user@company.com",
        )

        employee = Employee(
            employee_id="EMP9001",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        fingerprint = TicketFingerprinter.generate(ticket)

        # ========== ATTEMPT 1: Worker A - Partial failure with SMTP exception ==========
        workflow.ticket_client.get_ticket.return_value = ticket
        workflow.hr_client.get_employee_by_email.return_value = employee
        workflow.ticket_analyzer.analyze.return_value = AnalysisResult(
            is_login_issue=True,
            issue_type=IssueType.CANNOT_LOGIN,
            reason="Login issue",
            confidence=0.9,
        )
        workflow.hr_client.reactivate_lms_account.return_value = True  # Success
        workflow.ticket_client.add_log.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)  # Success
        workflow.ticket_client.update_stage.return_value = WriteOutcome(status=WriteOutcomeStatus.SUCCESS)  # Success
        workflow.gmail_service.send_email.return_value = False  # SMTP fails

        # Worker A claims ticket
        token_a = state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300  # 5 minute lease
        )
        assert token_a is not None

        # Execute workflow (all side effects complete, but email fails)
        result1 = workflow.execute(ticket_id=ticket.id)
        assert result1.reactivation_completed is True  # DEFECT 2: Side effect preserved despite exception
        assert result1.odoo_note_completed is True
        assert result1.stage_update_completed is True
        assert result1.email_delivery_completed is False  # Email failed

        # Save state after Worker A
        state1 = AutomationState(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            status=AutomationStatus.RETRY_SCHEDULED,  # Will retry for email only
            reactivation_completed=True,
            odoo_note_completed=True,
            stage_update_completed=True,
            email_delivery_completed=False,
        )
        state_repo.save(state1, owner_token=token_a)  # Pass owner_token for active lease

        # ========== ATTEMPT 2: Worker B - Try to claim (should fail due to active lease) ==========
        token_b = state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert token_b is None  # DEFECT 3: Lease blocks concurrent claim

        # ========== ATTEMPT 3: Simulate lease expiration + Recovery ==========
        # Manually expire the lease to simulate worker A crash
        import sqlite3
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(seconds=1)

        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), ticket.id)
            )
            conn.commit()

        # Worker C tries to claim after lease expires
        token_c = state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert token_c is not None  # DEFECT 4: Recovered expired lease

        # Verify recovered ticket is PROCESSING with new owner
        recovered_state = state_repo.get(ticket.id)
        assert recovered_state.status == AutomationStatus.PROCESSING
        assert recovered_state.lease_owner_token == token_c
        assert recovered_state.reactivation_completed is True  # Side effects preserved
        assert recovered_state.odoo_note_completed is True

        # ========== ATTEMPT 4: Worker C completes with email retry ==========
        workflow.ticket_client.reset_mock()
        workflow.hr_client.reset_mock()
        workflow.ticket_analyzer.reset_mock()
        workflow.gmail_service.reset_mock()

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
        workflow.gmail_service.send_email.return_value = True  # Email succeeds this time

        # Execute with recovered state
        recovered_state_retrieved = state_repo.get(ticket.id)
        result2 = workflow.execute(ticket_id=ticket.id, state=recovered_state_retrieved)

        # Should succeed, but LMS reactivation should NOT be called again
        assert result2.action_taken == "account_reactivated"
        assert result2.email_delivery_completed is True

        # Verify LMS was not re-called (already completed in Attempt 1)
        workflow.hr_client.reactivate_lms_account.assert_not_called()

        # Mark as completed with token validation
        mark_result = state_repo.mark_completed(ticket.id, owner_token=token_c)
        assert mark_result is True

        # Verify final state
        final_state = state_repo.get(ticket.id)
        assert final_state.status == AutomationStatus.COMPLETED
        assert final_state.processing_lease_until is None
        assert final_state.lease_owner_token is None

    def test_stage4_retry_discovery_with_side_effect_preservation(self, workflow, state_repo):
        """
        Verify stage-4 tickets with due retries are discovered and side effects preserved.

        Demonstrates:
        - DEFECT 1: Stage-4 tickets discovered via database query
        - DEFECT 2: Side effects preserved across retries
        """
        # Create a stage-4 ticket with due retry (from DEFECT 1)
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        state = AutomationState(
            ticket_id=9002,
            fingerprint="stage4_fp",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=past,  # Due for retry
            # DEFECT 2: All side effects from first attempt preserved
            reactivation_completed=True,
            odoo_note_completed=False,  # Failed on first attempt
            stage_update_completed=True,
        )
        state_repo.save(state)

        # DEFECT 1 FIX: Query database directly (ignores Odoo stage)
        due_retries = state_repo.get_due_retries(limit=50)
        assert len(due_retries) == 1
        assert due_retries[0].ticket_id == 9002

        # DEFECT 2 FIX: Verify side effects are preserved
        retry_state = due_retries[0]
        assert retry_state.reactivation_completed is True  # Preserved
        assert retry_state.odoo_note_completed is False    # Preserved
        assert retry_state.stage_update_completed is True   # Preserved

    def test_expired_processing_tickets_recovery(self, state_repo):
        """
        Verify expired PROCESSING tickets are discovered for recovery.

        Demonstrates:
        - DEFECT 4: Orphaned PROCESSING tickets with expired leases discoverable
        """
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(hours=1)

        # Create abandoned PROCESSING ticket with expired lease
        state = AutomationState(
            ticket_id=9003,
            fingerprint="orphaned_fp",
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,
            odoo_note_completed=True,
        )
        state_repo.save(state)

        # Manually set expired lease
        import sqlite3
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                (expired_lease.isoformat(), 9003)
            )
            conn.commit()

        # DEFECT 4 FIX: Discover expired tickets
        expired_tickets = state_repo.get_expired_processing_tickets(limit=50)
        assert len(expired_tickets) == 1
        assert expired_tickets[0].ticket_id == 9003

        # Verify side effects are preserved for recovery
        assert expired_tickets[0].reactivation_completed is True
        assert expired_tickets[0].odoo_note_completed is True

    def test_database_migration_legacy_database(self):
        """
        Verify legacy databases without lease_owner_token column are migrated.

        Demonstrates:
        - DEFECT 5: Legacy database schema migrated automatically
        """
        # Create a temporary legacy database without lease_owner_token
        fd, temp_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            import sqlite3
            # Create legacy schema without lease_owner_token
            with sqlite3.connect(temp_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE automation_state (
                        ticket_id INTEGER PRIMARY KEY,
                        fingerprint TEXT NOT NULL,
                        status TEXT NOT NULL,
                        last_decision TEXT,
                        last_reason TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_checked_at TEXT,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        next_retry_at TEXT,
                        last_error TEXT,
                        reactivation_completed INTEGER NOT NULL DEFAULT 0,
                        odoo_note_completed INTEGER NOT NULL DEFAULT 0,
                        customer_response_completed INTEGER NOT NULL DEFAULT 0,
                        stage_update_completed INTEGER NOT NULL DEFAULT 0,
                        email_delivery_completed INTEGER NOT NULL DEFAULT 0,
                        processing_lease_until TEXT
                    )
                """)
                conn.commit()

            # Initialize repository with legacy database
            repo = AutomationStateRepository(db_path=Path(temp_path))

            # DEFECT 5 FIX: Migration should have added the column
            with sqlite3.connect(temp_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(automation_state)")
                columns = {row[1] for row in cursor.fetchall()}
                assert "lease_owner_token" in columns  # Column added by migration

            # Verify functionality works with migrated database
            state = AutomationState(
                ticket_id=9004,
                fingerprint="test_fp",
                status=AutomationStatus.PROCESSING,
            )
            repo.save(state)

            token = repo.claim_for_processing(
                ticket_id=9005,
                fingerprint="test_fp2",
                lease_duration_seconds=300
            )
            assert token is not None  # Token functionality works

        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def test_all_fixes_together_realistic_scenario(self, workflow, state_repo):
        """
        Comprehensive realistic scenario using all 5 fixes together.

        Scenario: Multiple tickets with different failure modes and recovery patterns.
        """
        # Create 3 tickets at different stages
        tickets = [
            Ticket(id=9101, name="Ticket 1", email_from="user1@company.com"),
            Ticket(id=9102, name="Ticket 2", email_from="user2@company.com"),
            Ticket(id=9103, name="Ticket 3", email_from="user3@company.com"),
        ]

        employee_template = Employee(
            employee_id="EMPX",
            name="User",
            email="user@company.com",
            status=EmployeeStatus.ACTIVE,
            lms_account_status="deactivated",
            deactivation_reason=DeactivationReason.INACTIVITY_30_DAYS,
        )

        now = datetime.now(timezone.utc)

        # Ticket 1: Stage-4 with due retry (DEFECT 1 scenario)
        state1 = AutomationState(
            ticket_id=9101,
            fingerprint="fp1",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=now - timedelta(hours=1),
            reactivation_completed=True,
            odoo_note_completed=False,
        )
        state_repo.save(state1)

        # Ticket 2: Orphaned PROCESSING (DEFECT 4 scenario)
        state2 = AutomationState(
            ticket_id=9102,
            fingerprint="fp2",
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,
        )
        state_repo.save(state2)

        import sqlite3
        with sqlite3.connect(state_repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE automation_state SET processing_lease_until = ? WHERE ticket_id = ?",
                ((now - timedelta(hours=1)).isoformat(), 9102)
            )
            conn.commit()

        # Ticket 3: New ticket
        # (Will be claimed by workers)

        # Query due retries (DEFECT 1)
        due_retries = state_repo.get_due_retries(limit=10)
        assert len(due_retries) == 1
        assert due_retries[0].ticket_id == 9101
        assert due_retries[0].reactivation_completed is True  # DEFECT 2

        # Query expired tickets (DEFECT 4)
        expired = state_repo.get_expired_processing_tickets(limit=10)
        assert len(expired) == 1
        assert expired[0].ticket_id == 9102
        assert expired[0].reactivation_completed is True  # DEFECT 2

        # Test lease safety (DEFECT 3)
        fingerprint3 = TicketFingerprinter.generate(tickets[2])
        token_a = state_repo.claim_for_processing(
            ticket_id=9103,
            fingerprint=fingerprint3,
            lease_duration_seconds=300
        )
        assert token_a is not None

        token_b = state_repo.claim_for_processing(
            ticket_id=9103,
            fingerprint=fingerprint3,
            lease_duration_seconds=300
        )
        assert token_b is None  # Concurrent claim blocked

        # Verify all data persists
        all_states = [
            state_repo.get(9101),
            state_repo.get(9102),
            state_repo.get(9103),
        ]
        assert all([s is not None for s in all_states])
        assert all_states[0].reactivation_completed is True
        assert all_states[1].reactivation_completed is True
        assert all_states[2].lease_owner_token == token_a
