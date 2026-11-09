"""Regression tests for Issue #4: Distinguish Claim Contention from SQLite Failure.

Tests that claim_for_processing() failures are properly distinguished from legitimate
worker contention and reported as persistence failures.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from srcs.main import AutomationExecutor
from srcs.models import (
    AutomationState, AutomationStatus, Ticket, Employee,
    EmployeeStatus, DeactivationReason
)
from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.services.ticket_analyzer import IssueType, AnalysisResult
from srcs.services.login_workflow import WorkflowResult
from srcs.services.ticket_poller import PollingMetrics


class TestClaimPersistenceDistinction:
    """Tests for distinguishing claim contention from SQLite persistence failures."""

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

    @pytest.fixture
    def executor(self, state_repo):
        """Create AutomationExecutor with mocked dependencies."""
        executor = AutomationExecutor(
            ticket_client=Mock(),
            hr_client=Mock(),
            ticket_analyzer=Mock(),
            gmail_service=Mock(),
            state_repo=state_repo
        )
        executor.poller = Mock()
        executor.poller.poll.return_value = []
        executor.poller.poll_for_retry.return_value = []
        executor.metrics = PollingMetrics()
        executor.workflow = Mock()
        state_repo.get_expired_processing_tickets = Mock(return_value=[])
        state_repo.get_due_retries = Mock(return_value=[])
        return executor

    def test_claim_sqlite_exception_is_persistence_failure(self, executor, state_repo):
        """When claim_for_processing() raises SQLite exception, result has success=False and persistence_failures > 0."""
        ticket = Ticket(
            id=11001,
            name="Cannot login",
            email_from="user@company.com"
        )

        # Setup executor
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket

        # Mock claim_for_processing to raise SQLite exception
        original_claim = state_repo.claim_for_processing
        def mock_claim_raises(*args, **kwargs):
            raise sqlite3.OperationalError("Database locked during claim")

        state_repo.claim_for_processing = mock_claim_raises

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False when claim raises exception
        assert result["success"] is False, \
            "Result must have success=False when claim_for_processing() raises exception"

        # VERIFY: persistence_failures counter > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0 when claim raises exception"

        # VERIFY: skipped should NOT increase (this is not legitimate contention)
        assert result["skipped"] == 0, \
            "skipped should be 0 when claim fails with exception, not counted as skip"

        # VERIFY: failed should increase
        assert result["failed"] > 0, \
            "failed should be > 0 when claim raises exception"

        # VERIFY: error_details includes claim context
        assert any("claim_for_processing" in detail for detail in result["error_details"]), \
            "error_details must identify claim_for_processing operation"

    def test_claim_database_unavailable_not_counted_as_skip(self, executor, state_repo):
        """Database unavailability during claim is not counted as legitimate skip."""
        ticket = Ticket(
            id=11002,
            name="Cannot login",
            email_from="user@company.com"
        )

        # Setup executor
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket

        # Mock claim_for_processing to raise database unavailable error
        def mock_claim_db_unavailable(*args, **kwargs):
            raise sqlite3.OperationalError("unable to open database file")

        state_repo.claim_for_processing = mock_claim_db_unavailable

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: success=False
        assert result["success"] is False, \
            "Result must be unsuccessful when database is unavailable"

        # VERIFY: persistence_failures > 0
        assert result["persistence_failures"] > 0, \
            "Database unavailability must be recorded as persistence failure"

        # VERIFY: NOT counted as skipped
        assert result["skipped"] == 0, \
            "Database failure should NOT be counted as skipped"

        # VERIFY: failed > 0
        assert result["failed"] > 0, \
            "Database failure should be counted as failed"

    def test_legitimate_active_lease_contention_is_skip(self, executor, state_repo):
        """Active lease held by another worker correctly returns None and is counted as skip."""
        ticket = Ticket(
            id=11003,
            name="Cannot login",
            email_from="user@company.com"
        )

        # First, claim the ticket for processing
        fp = TicketFingerprinter.generate(ticket)
        token = state_repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fp,
            lease_duration_seconds=300
        )
        assert token is not None, "Initial claim should succeed"

        # Setup executor to try to claim same ticket (simulating another worker)
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket
        executor.workflow.execute = Mock()  # Should not be called

        # Run executor (will attempt to claim but should get None due to active lease)
        result = executor.run_once(limit=10)

        # VERIFY: success=True (legitimate contention is not a persistence failure)
        assert result["success"] is True, \
            "Legitimate worker contention should not cause success=False"

        # VERIFY: persistence_failures == 0
        assert result["persistence_failures"] == 0, \
            "Legitimate contention is not a persistence failure"

        # VERIFY: skipped increased (legitimate contention)
        assert result["skipped"] > 0, \
            "Legitimate active lease contention should be counted as skipped"

        # VERIFY: workflow NOT executed (no token)
        assert not executor.workflow.execute.called, \
            "Workflow should not execute without valid claim"

    def test_cli_nonzero_exit_when_claim_persistence_fails(self, executor, state_repo):
        """CLI should exit with nonzero code when claim persistence fails."""
        ticket = Ticket(
            id=11004,
            name="Cannot login",
            email_from="user@company.com"
        )

        # Setup executor
        executor.poller.poll.return_value = [ticket]
        executor.ticket_client.get_ticket.return_value = ticket

        # Mock claim_for_processing to raise exception
        def mock_claim_fails(*args, **kwargs):
            raise sqlite3.OperationalError("Disk I/O error")

        state_repo.claim_for_processing = mock_claim_fails

        # Run executor
        result = executor.run_once(limit=10)

        # VERIFY: result["success"] is False (which CLI will use for exit code)
        assert result["success"] is False, \
            "result[\"success\"] must be False for claim persistence failure"

        # VERIFY: persistence_failures > 0
        assert result["persistence_failures"] > 0, \
            "persistence_failures must be > 0"

        # VERIFY: error_details includes claim context
        assert any("claim_for_processing" in detail for detail in result["error_details"]), \
            "error_details must identify claim_for_processing"
