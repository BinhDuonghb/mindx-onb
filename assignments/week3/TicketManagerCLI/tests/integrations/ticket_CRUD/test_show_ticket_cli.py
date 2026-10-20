import subprocess
import sys
from uuid import UUID

from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.services.ticketService import TicketService


def run_cli_show(ticket_id) -> subprocess.CompletedProcess:
    """Helper to run show command with ticket ID."""
    cmd = [sys.executable, "main.py", "--test", "show", str(ticket_id)]
    return subprocess.run(cmd, capture_output=True, text=True)


def setup_tickets(db_path, tickets_data):
    """Helper to setup test tickets in the file."""
    db_client = DBClient(db_path)
    ticket_service = TicketService(db_client)

    created = []
    for data in tickets_data:
        ticket = Ticket(id=None, **data)
        created.append(ticket_service.create(ticket))

    return created


class TestShowTicketCLI:
    """Test the show ticket CLI command."""

    def test_show_ticket_displays_all_fields(self, use_temp_test_database):
        """Should display all ticket fields."""
        tickets = setup_tickets(use_temp_test_database, [
            {
                "title": "Important Bug",
                "description": "System is down",
                "status": "open",
                "priority": "high",
                "tags": ["bug", "urgent"],
            },
        ])

        ticket_id = tickets[0].id
        result = run_cli_show(ticket_id)

        assert result.returncode == 0
        assert "Important Bug" in result.stdout
        assert "System is down" in result.stdout
        assert "high" in result.stdout.lower()
        assert "open" in result.stdout.lower()

    def test_show_ticket_with_uuid(self, use_temp_test_database):
        """Should accept UUID as ticket ID."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "Test Task"},
        ])

        ticket_id = tickets[0].id
        result = run_cli_show(ticket_id)

        assert result.returncode == 0
        assert "Test Task" in result.stdout

    def test_show_nonexistent_ticket_fails(self, use_temp_test_database):
        """Should fail when ticket ID doesn't exist."""
        fake_uuid = UUID("00000000-0000-0000-0000-000000000000")
        result = run_cli_show(fake_uuid)

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_show_ticket_displays_description(self, use_temp_test_database):
        """Should display full description."""
        tickets = setup_tickets(use_temp_test_database, [
            {
                "title": "Feature Request",
                "description": "Add dark mode to the application for better user experience",
            },
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        assert "Add dark mode" in result.stdout

    def test_show_ticket_displays_priority(self, use_temp_test_database):
        """Should display ticket priority."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "Low Priority Task", "priority": "low"},
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        assert "low" in result.stdout.lower()

    def test_show_ticket_displays_status(self, use_temp_test_database):
        """Should display ticket status."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "Closed Task", "status": "closed"},
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        assert "closed" in result.stdout.lower()

    def test_show_ticket_displays_tags(self, use_temp_test_database):
        """Should display all ticket tags."""
        tickets = setup_tickets(use_temp_test_database, [
            {
                "title": "Tagged Task",
                "tags": ["bug", "frontend", "urgent"],
            },
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        assert "bug" in result.stdout
        assert "frontend" in result.stdout
        assert "urgent" in result.stdout

    def test_show_ticket_displays_id(self, use_temp_test_database):
        """Should display the ticket ID."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "Task with ID"},
        ])

        ticket_id = tickets[0].id
        result = run_cli_show(ticket_id)

        assert result.returncode == 0
        assert str(ticket_id) in result.stdout

    def test_show_ticket_with_empty_description(self, use_temp_test_database):
        """Should handle empty description gracefully."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "No Description Task", "description": ""},
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        assert "No Description Task" in result.stdout

    def test_show_ticket_with_no_tags(self, use_temp_test_database):
        """Should handle ticket with no tags."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "Untagged Task", "tags": []},
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        assert "Untagged Task" in result.stdout

    def test_show_invalid_id_format_fails(self, use_temp_test_database):
        """Should fail with invalid UUID format."""
        result = run_cli_show("not-a-uuid")

        assert result.returncode != 0

    def test_show_ticket_displays_created_at(self, use_temp_test_database):
        """Should display ticket creation timestamp."""
        tickets = setup_tickets(use_temp_test_database, [
            {"title": "Task with Timestamp"},
        ])

        result = run_cli_show(tickets[0].id)

        assert result.returncode == 0
        # Should contain ISO format datetime
        assert "T" in result.stdout or "20" in result.stdout  # Year in timestamp
