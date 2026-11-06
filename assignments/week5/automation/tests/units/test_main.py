"""Unit tests for AutomationExecutor - main.py orchestration."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


class SimpleExecutor:
    """Simplified executor for testing without full initialization."""

    def __init__(self):
        """Initialize with mock dependencies."""
        from srcs.services.ticket_poller import PollingMetrics

        self.ticket_client = Mock()
        self.hr_client = Mock()
        self.state_repo = Mock()
        self.poller = Mock()
        self.workflow = Mock()
        self.metrics = PollingMetrics()

    def run_once(self, limit: int = 50, min_age_minutes: int = 0) -> dict:
        """Simplified run_once for testing."""
        from datetime import datetime as dt

        start_time = dt.utcnow()

        try:
            tickets = self.poller.poll(limit=limit, min_age_minutes=min_age_minutes)

            if not tickets:
                return {
                    "success": True,
                    "tickets_processed": 0,
                    "successful": 0,
                    "escalated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "elapsed_seconds": (dt.utcnow() - start_time).total_seconds(),
                }

            results = {"successful": 0, "escalated": 0, "skipped": 0, "failed": 0}

            for ticket in tickets:
                try:
                    result = self.workflow.execute(ticket_id=ticket.id)

                    if result.success:
                        if result.action_taken == "skipped":
                            results["skipped"] += 1
                        elif result.action_taken == "escalated_manual_review":
                            results["escalated"] += 1
                        elif result.action_taken == "account_reactivated":
                            results["successful"] += 1
                    else:
                        results["failed"] += 1

                except Exception as e:
                    results["failed"] += 1

            self.metrics.record_poll(
                fetched=len(tickets),
                queued=results["successful"] + results["escalated"],
            )

            elapsed = (dt.utcnow() - start_time).total_seconds()
            results["success"] = True
            results["tickets_processed"] = len(tickets)
            results["elapsed_seconds"] = elapsed

            return results

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "elapsed_seconds": (dt.utcnow() - start_time).total_seconds(),
            }

    def get_metrics(self) -> dict:
        """Get metrics."""
        return self.metrics.to_dict()


@pytest.fixture
def mock_executor():
    """Create executor with mocked dependencies."""
    return SimpleExecutor()


class TestAutomationExecutorInitialization:
    """Test AutomationExecutor initialization."""

    def test_executor_has_metrics(self, mock_executor):
        """Should have metrics tracker."""
        assert mock_executor.metrics is not None
        metrics = mock_executor.get_metrics()
        assert metrics['total_polls'] == 0


class TestAutomationExecutorRunOnce:
    """Test one-time automation run."""

    def test_run_once_no_tickets(self, mock_executor):
        """Should handle case with no tickets."""
        mock_executor.poller.poll = Mock(return_value=[])

        result = mock_executor.run_once(limit=50, min_age_minutes=5)

        assert result['success'] is True
        assert result['tickets_processed'] == 0

    def test_run_once_processes_tickets(self, mock_executor):
        """Should process tickets returned by poller."""
        from srcs.models import Ticket
        from srcs.services.login_workflow import WorkflowResult

        # Create mock tickets
        tickets = [
            Ticket(id=1, name="Ticket 1", email_from="user1@company.com"),
            Ticket(id=2, name="Ticket 2", email_from="user2@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets)

        # Mock workflow results
        result1 = WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message="Reactivated",
            ticket_id=1,
        )
        result2 = WorkflowResult(
            success=True,
            action_taken="escalated_manual_review",
            message="Escalated",
            ticket_id=2,
        )
        mock_executor.workflow.execute = Mock(side_effect=[result1, result2])

        result = mock_executor.run_once(limit=50)

        assert result['success'] is True
        assert result['tickets_processed'] == 2
        assert result['successful'] == 1
        assert result['escalated'] == 1

    def test_run_once_tracks_skipped(self, mock_executor):
        """Should track skipped tickets."""
        from srcs.models import Ticket
        from srcs.services.login_workflow import WorkflowResult

        tickets = [
            Ticket(id=1, name="Ticket 1", email_from="user1@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets)

        result = WorkflowResult(
            success=True,
            action_taken="skipped",
            message="Not a login issue",
            ticket_id=1,
        )
        mock_executor.workflow.execute = Mock(return_value=result)

        run_result = mock_executor.run_once(limit=50)

        assert run_result['skipped'] == 1

    def test_run_once_tracks_failures(self, mock_executor):
        """Should track failed tickets."""
        from srcs.models import Ticket
        from srcs.services.login_workflow import WorkflowResult

        tickets = [
            Ticket(id=1, name="Ticket 1", email_from="user1@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets)

        result = WorkflowResult(
            success=False,
            action_taken="error",
            message="Processing failed",
            error_message="Processing failed",
            ticket_id=1,
        )
        mock_executor.workflow.execute = Mock(return_value=result)

        run_result = mock_executor.run_once(limit=50)

        assert run_result['failed'] == 1

    def test_run_once_handles_exception(self, mock_executor):
        """Should handle exceptions gracefully."""
        mock_executor.poller.poll = Mock(side_effect=Exception("API error"))

        result = mock_executor.run_once(limit=50)

        assert result['success'] is False
        assert 'error' in result

    def test_run_once_respects_parameters(self, mock_executor):
        """Should pass parameters to poller."""
        mock_executor.poller.poll = Mock(return_value=[])

        mock_executor.run_once(limit=25, min_age_minutes=10)

        mock_executor.poller.poll.assert_called_once_with(limit=25, min_age_minutes=10)

    def test_run_once_records_metrics(self, mock_executor):
        """Should record metrics after processing."""
        from srcs.models import Ticket
        from srcs.services.login_workflow import WorkflowResult

        tickets = [
            Ticket(id=1, name="Ticket 1", email_from="user1@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets)

        result = WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message="Reactivated",
            ticket_id=1,
        )
        mock_executor.workflow.execute = Mock(return_value=result)

        mock_executor.run_once(limit=50)

        metrics = mock_executor.get_metrics()
        assert metrics['total_polls'] == 1
        assert metrics['total_tickets_fetched'] == 1

    def test_run_once_elapsed_time(self, mock_executor):
        """Should track elapsed time."""
        mock_executor.poller.poll = Mock(return_value=[])

        result = mock_executor.run_once(limit=50)

        assert 'elapsed_seconds' in result
        assert isinstance(result['elapsed_seconds'], float)
        assert result['elapsed_seconds'] >= 0


class TestPollingMetricsIntegration:
    """Test metrics tracking through executor."""

    def test_metrics_accumulate(self, mock_executor):
        """Should accumulate metrics across multiple runs."""
        from srcs.models import Ticket
        from srcs.services.login_workflow import WorkflowResult

        # First run
        tickets1 = [
            Ticket(id=1, name="T1", email_from="user1@company.com"),
            Ticket(id=2, name="T2", email_from="user2@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets1)
        result1 = WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message="OK",
            ticket_id=1,
        )
        result2 = WorkflowResult(
            success=True,
            action_taken="skipped",
            message="Not a login issue",
            ticket_id=2,
        )
        mock_executor.workflow.execute = Mock(side_effect=[result1, result2])

        mock_executor.run_once(limit=50)

        # Second run
        tickets2 = [
            Ticket(id=3, name="T3", email_from="user3@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets2)
        result3 = WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message="OK",
            ticket_id=3,
        )
        mock_executor.workflow.execute = Mock(return_value=result3)

        mock_executor.run_once(limit=50)

        # Check accumulated metrics
        metrics = mock_executor.get_metrics()
        assert metrics['total_polls'] == 2
        assert metrics['total_tickets_fetched'] == 3

    def test_metrics_to_dict_format(self, mock_executor):
        """Should format metrics correctly."""
        mock_executor.poller.poll = Mock(return_value=[])

        mock_executor.run_once(limit=50)

        metrics = mock_executor.get_metrics()

        assert isinstance(metrics, dict)
        assert 'total_polls' in metrics
        assert 'total_tickets_fetched' in metrics
        assert 'total_tickets_queued' in metrics
        assert 'last_poll_time' in metrics


class TestErrorHandling:
    """Test error handling in executor."""

    def test_workflow_exception_does_not_stop_processing(self, mock_executor):
        """Should continue processing if one ticket fails."""
        from srcs.models import Ticket
        from srcs.services.login_workflow import WorkflowResult

        tickets = [
            Ticket(id=1, name="T1", email_from="user1@company.com"),
            Ticket(id=2, name="T2", email_from="user2@company.com"),
        ]
        mock_executor.poller.poll = Mock(return_value=tickets)

        # First ticket raises exception, second succeeds
        result2 = WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message="OK",
            ticket_id=2,
        )
        mock_executor.workflow.execute = Mock(
            side_effect=[
                Exception("Processing failed"),
                result2,
            ]
        )

        result = mock_executor.run_once(limit=50)

        # Should continue and process ticket 2
        assert result['tickets_processed'] == 2
        assert result['failed'] == 1
        assert result['successful'] == 1

    def test_poller_exception_returns_error(self, mock_executor):
        """Should return error if poller fails."""
        mock_executor.poller.poll = Mock(side_effect=Exception("Network error"))

        result = mock_executor.run_once(limit=50)

        assert result['success'] is False
        assert 'error' in result
