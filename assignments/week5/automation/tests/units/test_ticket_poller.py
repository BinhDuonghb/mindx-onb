"""Unit tests for TicketPoller."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from srcs.models import Ticket, AutomationState, AutomationStatus
from srcs.services.ticket_poller import TicketPoller, PollingMetrics
from srcs.services.ticket_fingerprinter import TicketFingerprinter


@pytest.fixture
def mock_ticket_client():
    """Mock ticket client."""
    client = Mock()
    client.search_tickets = Mock(return_value=[])
    return client


@pytest.fixture
def mock_state_repo():
    """Mock state repository."""
    repo = Mock()
    repo.get = Mock(return_value=None)
    return repo


@pytest.fixture
def poller(mock_ticket_client, mock_state_repo):
    """Create TicketPoller with mocked dependencies."""
    return TicketPoller(
        ticket_client=mock_ticket_client,
        state_repo=mock_state_repo,
    )


class TestTicketPollerPoll:
    """Test ticket polling."""

    def test_poll_no_tickets_found(self, poller, mock_ticket_client):
        """Should return empty list when no tickets found."""
        mock_ticket_client.search_tickets.return_value = []

        result = poller.poll(limit=50)

        assert result == []
        mock_ticket_client.search_tickets.assert_called_once()

    def test_poll_returns_new_tickets(self, poller, mock_ticket_client, mock_state_repo):
        """Should return new tickets never processed before."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )
        mock_ticket_client.search_tickets.return_value = [ticket]
        mock_state_repo.get.return_value = None  # No prior state

        result = poller.poll(limit=50)

        assert len(result) == 1
        assert result[0].id == 1

    def test_poll_respects_limit(self, poller, mock_ticket_client, mock_state_repo):
        """Should respect limit parameter."""
        tickets = [
            Ticket(id=i, name=f"Ticket {i}", email_from="user@company.com")
            for i in range(1, 11)
        ]
        mock_ticket_client.search_tickets.return_value = tickets
        mock_state_repo.get.return_value = None

        result = poller.poll(limit=5)

        # Should call search_tickets with limit
        call_args = mock_ticket_client.search_tickets.call_args
        assert call_args[1]["limit"] == 5

    def test_poll_skips_already_processing(self, poller, mock_ticket_client, mock_state_repo):
        """Should skip tickets already being processed."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )
        mock_ticket_client.search_tickets.return_value = [ticket]

        # Ticket is already processing
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.PROCESSING,
        )
        mock_state_repo.get.return_value = state

        result = poller.poll(limit=50)

        assert len(result) == 0

    def test_poll_detects_content_change(self, poller, mock_ticket_client, mock_state_repo):
        """Should re-queue ticket if content changed."""
        ticket = Ticket(
            id=1,
            name="Cannot login - URGENT",
            email_from="user@company.com",
        )
        mock_ticket_client.search_tickets.return_value = [ticket]

        # Previous state with different fingerprint
        old_fingerprint = "old_fingerprint"
        state = AutomationState(
            ticket_id=1,
            fingerprint=old_fingerprint,
            status=AutomationStatus.COMPLETED,
        )
        mock_state_repo.get.return_value = state

        result = poller.poll(limit=50)

        # Should be queued because content changed
        assert len(result) == 1

    def test_poll_skips_unchanged_content(self, poller, mock_ticket_client, mock_state_repo):
        """Should skip tickets with unchanged content."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )
        mock_ticket_client.search_tickets.return_value = [ticket]

        # Previous state with same fingerprint
        fingerprint = TicketFingerprinter.generate(ticket)
        state = AutomationState(
            ticket_id=1,
            fingerprint=fingerprint,
            status=AutomationStatus.COMPLETED,
        )
        mock_state_repo.get.return_value = state

        result = poller.poll(limit=50)

        # Should not be queued - content unchanged
        assert len(result) == 0

    def test_poll_respects_min_age(self, poller, mock_ticket_client, mock_state_repo):
        """Should skip very new tickets."""
        now = datetime.utcnow()
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            create_date=now,  # Just created
        )
        mock_ticket_client.search_tickets.return_value = [ticket]
        mock_state_repo.get.return_value = None

        # Require tickets to be at least 5 minutes old
        result = poller.poll(limit=50, min_age_minutes=5)

        # Should be skipped - too new
        assert len(result) == 0

    def test_poll_includes_old_tickets(self, poller, mock_ticket_client, mock_state_repo):
        """Should include tickets old enough."""
        now = datetime.utcnow()
        old_time = now - timedelta(minutes=10)
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            create_date=old_time,
        )
        mock_ticket_client.search_tickets.return_value = [ticket]
        mock_state_repo.get.return_value = None

        # Require tickets to be at least 5 minutes old
        result = poller.poll(limit=50, min_age_minutes=5)

        # Should be included - old enough
        assert len(result) == 1

    def test_poll_mixed_tickets(self, poller, mock_ticket_client, mock_state_repo):
        """Should handle mix of new, unchanged, and changed tickets."""
        now = datetime.utcnow()

        ticket1 = Ticket(id=1, name="New ticket", email_from="user@company.com")
        ticket2 = Ticket(id=2, name="Unchanged", email_from="user@company.com")
        ticket3 = Ticket(id=3, name="Updated", email_from="user@company.com")

        mock_ticket_client.search_tickets.return_value = [ticket1, ticket2, ticket3]

        def get_state(ticket_id):
            if ticket_id == 1:
                return None  # New ticket
            elif ticket_id == 2:
                fp = TicketFingerprinter.generate(ticket2)
                return AutomationState(
                    ticket_id=2,
                    fingerprint=fp,
                    status=AutomationStatus.COMPLETED,
                )
            elif ticket_id == 3:
                return AutomationState(
                    ticket_id=3,
                    fingerprint="old_fp",
                    status=AutomationStatus.COMPLETED,
                )

        mock_state_repo.get.side_effect = get_state

        result = poller.poll(limit=50)

        # Should include ticket1 (new) and ticket3 (changed)
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 3

    def test_poll_handles_exception(self, poller, mock_ticket_client):
        """Should handle exceptions gracefully."""
        mock_ticket_client.search_tickets.side_effect = Exception("API error")

        result = poller.poll(limit=50)

        assert result == []

    def test_poll_search_params(self, poller, mock_ticket_client, mock_state_repo):
        """Should search with correct parameters."""
        mock_ticket_client.search_tickets.return_value = []

        poller.poll(limit=25)

        call_args = mock_ticket_client.search_tickets.call_args
        assert call_args[1]["domain"] == [("stage_id", "in", [1, 2])]
        assert call_args[1]["limit"] == 25


class TestTicketPollerPollForRetry:
    """Test retry polling."""

    def test_poll_for_retry_no_retries(self, poller, mock_ticket_client, mock_state_repo):
        """Should return empty list when no retries found."""
        mock_ticket_client.search_tickets.return_value = []

        result = poller.poll_for_retry(limit=50)

        assert result == []

    def test_poll_for_retry_finds_ready_retries(self, poller, mock_ticket_client, mock_state_repo):
        """Should find tickets ready for retry."""
        ticket = Ticket(id=1, name="Test", email_from="user@company.com")
        mock_ticket_client.search_tickets.return_value = [ticket]

        # Create state ready for retry
        past_time = datetime.utcnow() - timedelta(hours=1)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=past_time,  # Ready to retry
        )
        mock_state_repo.get.return_value = state

        result = poller.poll_for_retry(limit=50)

        assert len(result) == 1
        assert result[0][0].id == 1
        assert result[0][1].status == AutomationStatus.RETRY_SCHEDULED

    def test_poll_for_retry_skips_future_retries(self, poller, mock_ticket_client, mock_state_repo):
        """Should skip retries not yet ready."""
        ticket = Ticket(id=1, name="Test", email_from="user@company.com")
        mock_ticket_client.search_tickets.return_value = [ticket]

        # Create state not ready for retry yet
        future_time = datetime.utcnow() + timedelta(hours=1)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=future_time,  # Not ready yet
        )
        mock_state_repo.get.return_value = state

        result = poller.poll_for_retry(limit=50)

        assert len(result) == 0

    def test_poll_for_retry_handles_exception(self, poller, mock_ticket_client):
        """Should handle exceptions gracefully."""
        mock_ticket_client.search_tickets.side_effect = Exception("API error")

        result = poller.poll_for_retry(limit=50)

        assert result == []

    def test_poll_for_retry_respects_limit(self, poller, mock_ticket_client, mock_state_repo):
        """Should respect limit parameter."""
        tickets = [
            Ticket(id=i, name=f"Test {i}", email_from="user@company.com")
            for i in range(1, 11)
        ]
        mock_ticket_client.search_tickets.return_value = tickets

        past_time = datetime.utcnow() - timedelta(hours=1)
        state = AutomationState(
            ticket_id=1,
            fingerprint="abc123",
            status=AutomationStatus.RETRY_SCHEDULED,
            next_retry_at=past_time,
        )

        def get_state(ticket_id):
            if ticket_id == 1:
                return state
            return None

        mock_state_repo.get.side_effect = get_state

        result = poller.poll_for_retry(limit=3)

        # Should stop after finding limit retries
        assert len(result) <= 3


class TestPollingMetrics:
    """Test polling metrics tracking."""

    def test_metrics_initialization(self):
        """Should initialize with zero values."""
        metrics = PollingMetrics()

        assert metrics.total_polls == 0
        assert metrics.total_tickets_fetched == 0
        assert metrics.total_tickets_queued == 0
        assert metrics.total_retries_found == 0
        assert metrics.last_poll_time is None

    def test_record_poll(self):
        """Should record poll metrics."""
        metrics = PollingMetrics()

        metrics.record_poll(fetched=10, queued=5)

        assert metrics.total_polls == 1
        assert metrics.total_tickets_fetched == 10
        assert metrics.total_tickets_queued == 5
        assert metrics.last_poll_time is not None
        assert metrics.last_poll_count == 5

    def test_record_multiple_polls(self):
        """Should accumulate multiple poll metrics."""
        metrics = PollingMetrics()

        metrics.record_poll(fetched=10, queued=5)
        metrics.record_poll(fetched=8, queued=4)
        metrics.record_poll(fetched=12, queued=6)

        assert metrics.total_polls == 3
        assert metrics.total_tickets_fetched == 30
        assert metrics.total_tickets_queued == 15

    def test_record_retry_poll(self):
        """Should record retry poll metrics."""
        metrics = PollingMetrics()

        metrics.record_retry_poll(retries=3)
        metrics.record_retry_poll(retries=2)

        assert metrics.total_retries_found == 5

    def test_metrics_to_dict(self):
        """Should convert metrics to dictionary."""
        metrics = PollingMetrics()
        metrics.record_poll(fetched=10, queued=5)

        result = metrics.to_dict()

        assert result["total_polls"] == 1
        assert result["total_tickets_fetched"] == 10
        assert result["total_tickets_queued"] == 5
        assert result["last_poll_count"] == 5
        assert result["last_poll_time"] is not None

    def test_metrics_with_no_polls(self):
        """Should handle metrics before any polls."""
        metrics = PollingMetrics()

        result = metrics.to_dict()

        assert result["total_polls"] == 0
        assert result["last_poll_time"] is None
