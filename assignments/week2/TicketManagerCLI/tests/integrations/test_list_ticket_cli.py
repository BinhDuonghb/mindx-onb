import subprocess
import sys
from uuid import UUID

from ticket_manager.config import TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.services.ticketService import TicketService


def run_cli_list(**kwargs) -> subprocess.CompletedProcess:
    """Helper to run list command with given arguments."""
    cmd = [sys.executable, "main.py", "--test", "list"]

    for key, value in kwargs.items():
        if value is not None:
            cmd.append(f"--{key}")
            cmd.append(str(value))

    return subprocess.run(cmd, capture_output=True, text=True)


def setup_tickets(tickets_data):
    """Helper to setup test tickets in the file."""
    TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")
    db_client = DBClient(TEST_TICKETS_FILE)
    ticket_service = TicketService(db_client)

    created = []
    for data in tickets_data:
        ticket = Ticket(id=None, **data)
        created.append(ticket_service.create(ticket))

    return created


class TestListTicketCLI:
    """Test the list ticket CLI command."""

    def test_list_empty_tickets(self):
        """Should display message when no tickets exist."""
        TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_list()

        assert result.returncode == 0

    def test_list_all_tickets(self):
        """Should list all tickets when no filters applied."""
        setup_tickets([
            {"title": "Task 1", "status": "open", "priority": "high"},
            {"title": "Task 2", "status": "closed", "priority": "low"},
            {"title": "Task 3", "status": "open", "priority": "medium"},
        ])

        result = run_cli_list()

        assert result.returncode == 0
        assert "Task 1" in result.stdout
        assert "Task 2" in result.stdout
        assert "Task 3" in result.stdout

    def test_list_filter_by_status_open(self):
        """Should filter tickets by open status."""
        setup_tickets([
            {"title": "Open Task 1", "status": "open"},
            {"title": "Closed Task", "status": "closed"},
            {"title": "Open Task 2", "status": "open"},
        ])

        result = run_cli_list(status="open")

        assert result.returncode == 0
        assert "Open Task 1" in result.stdout
        assert "Open Task 2" in result.stdout
        assert "Closed Task" not in result.stdout

    def test_list_filter_by_status_closed(self):
        """Should filter tickets by closed status."""
        setup_tickets([
            {"title": "Open Task", "status": "open"},
            {"title": "Closed Task 1", "status": "closed"},
            {"title": "Closed Task 2", "status": "closed"},
        ])

        result = run_cli_list(status="closed")

        assert result.returncode == 0
        assert "Closed Task 1" in result.stdout
        assert "Closed Task 2" in result.stdout
        assert "Open Task" not in result.stdout

    def test_list_filter_by_priority_high(self):
        """Should filter tickets by high priority."""
        setup_tickets([
            {"title": "High Priority Task 1", "priority": "high"},
            {"title": "Low Priority Task", "priority": "low"},
            {"title": "High Priority Task 2", "priority": "high"},
        ])

        result = run_cli_list(priority="high")

        assert result.returncode == 0
        assert "High Priority Task 1" in result.stdout
        assert "High Priority Task 2" in result.stdout
        assert "Low Priority Task" not in result.stdout

    def test_list_filter_by_priority_medium(self):
        """Should filter tickets by medium priority."""
        setup_tickets([
            {"title": "High Priority", "priority": "high"},
            {"title": "Medium Priority 1", "priority": "medium"},
            {"title": "Medium Priority 2", "priority": "medium"},
        ])

        result = run_cli_list(priority="medium")

        assert result.returncode == 0
        assert "Medium Priority 1" in result.stdout
        assert "Medium Priority 2" in result.stdout
        assert "High Priority" not in result.stdout

    def test_list_filter_by_priority_low(self):
        """Should filter tickets by low priority."""
        setup_tickets([
            {"title": "High Priority", "priority": "high"},
            {"title": "Low Priority 1", "priority": "low"},
            {"title": "Low Priority 2", "priority": "low"},
        ])

        result = run_cli_list(priority="low")

        assert result.returncode == 0
        assert "Low Priority 1" in result.stdout
        assert "Low Priority 2" in result.stdout
        assert "High Priority" not in result.stdout

    def test_list_filter_by_tag(self):
        """Should filter tickets by tag."""
        setup_tickets([
            {"title": "Bug Task 1", "tags": ["bug", "frontend"]},
            {"title": "Feature Task", "tags": ["feature"]},
            {"title": "Bug Task 2", "tags": ["bug", "backend"]},
        ])

        result = run_cli_list(tag="bug")

        assert result.returncode == 0
        assert "Bug Task 1" in result.stdout
        assert "Bug Task 2" in result.stdout
        assert "Feature Task" not in result.stdout

    def test_list_filter_by_multiple_tags(self):
        """Should handle filtering by different tags."""
        setup_tickets([
            {"title": "Frontend Bug", "tags": ["bug", "frontend"]},
            {"title": "Backend Bug", "tags": ["bug", "backend"]},
            {"title": "Urgent Feature", "tags": ["feature", "urgent"]},
        ])

        result = run_cli_list(tag="backend")

        assert result.returncode == 0
        assert "Backend Bug" in result.stdout
        assert "Frontend Bug" not in result.stdout

    def test_list_with_status_and_priority_filters(self):
        """Should handle multiple filters together."""
        setup_tickets([
            {"title": "Open High", "status": "open", "priority": "high"},
            {"title": "Open Low", "status": "open", "priority": "low"},
            {"title": "Closed High", "status": "closed", "priority": "high"},
        ])

        result = run_cli_list(status="open", priority="high")

        assert result.returncode == 0
        assert "Open High" in result.stdout
        assert "Open Low" not in result.stdout
        assert "Closed High" not in result.stdout

    def test_list_with_all_filters(self):
        """Should handle all filters simultaneously."""
        setup_tickets([
            {
                "title": "Matching Ticket",
                "status": "open",
                "priority": "high",
                "tags": ["bug", "urgent"],
            },
            {
                "title": "Different Status",
                "status": "closed",
                "priority": "high",
                "tags": ["bug"],
            },
            {
                "title": "Different Priority",
                "status": "open",
                "priority": "low",
                "tags": ["bug"],
            },
        ])

        result = run_cli_list(status="open", priority="high", tag="bug")

        assert result.returncode == 0
        assert "Matching Ticket" in result.stdout

    def test_list_invalid_status_fails(self):
        """Should fail with invalid status value."""
        result = run_cli_list(status="invalid-status")

        assert result.returncode != 0

    def test_list_invalid_priority_fails(self):
        """Should fail with invalid priority value."""
        result = run_cli_list(priority="critical")

        assert result.returncode != 0

    def test_list_no_results_with_filter(self):
        """Should handle no results from filter gracefully."""
        setup_tickets([
            {"title": "Open Task", "status": "open"},
            {"title": "Closed Task", "status": "closed"},
        ])

        result = run_cli_list(status="in-progress")

        assert result.returncode == 0

    def test_list_displays_ticket_info(self):
        """Should display relevant ticket information."""
        setup_tickets([
            {
                "title": "Important Bug",
                "description": "System down",
                "priority": "high",
                "status": "open",
            },
        ])

        result = run_cli_list()

        assert result.returncode == 0
        assert "Important Bug" in result.stdout
        assert "high" in result.stdout.lower()
