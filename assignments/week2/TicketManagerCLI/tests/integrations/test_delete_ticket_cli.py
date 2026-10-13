import subprocess
import sys
from uuid import UUID

from ticket_manager.config import TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.services.ticketService import TicketService


def run_cli_delete(ticket_id) -> subprocess.CompletedProcess:
    """Helper to run delete command with ticket ID."""
    cmd = [sys.executable, "main.py", "--test", "delete", str(ticket_id)]
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


class TestDeleteTicketCLI:
    """Test the delete ticket CLI command."""

    def test_delete_ticket_removes_from_list(self):
        """Should delete ticket and remove from list."""
        tickets = setup_tickets([
            {"title": "Task to Delete"},
        ])

        ticket_id = tickets[0].id
        result = run_cli_delete(ticket_id)

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        remaining = ticket_service.get_all()

        assert len(remaining) == 0
        assert ticket_service.get_by_id(ticket_id) is None

    def test_delete_ticket_leaves_others_intact(self):
        """Should delete only specified ticket, leaving others."""
        tickets = setup_tickets([
            {"title": "Keep Task 1"},
            {"title": "Delete Me"},
            {"title": "Keep Task 2"},
        ])

        run_cli_delete(tickets[1].id)

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        remaining = ticket_service.get_all()

        assert len(remaining) == 2
        assert ticket_service.get_by_id(tickets[0].id) is not None
        assert ticket_service.get_by_id(tickets[1].id) is None
        assert ticket_service.get_by_id(tickets[2].id) is not None

    def test_delete_first_ticket(self):
        """Should delete first ticket in list."""
        tickets = setup_tickets([
            {"title": "First to Delete"},
            {"title": "Second"},
            {"title": "Third"},
        ])

        run_cli_delete(tickets[0].id)

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        remaining = ticket_service.get_all()

        assert len(remaining) == 2
        assert remaining[0].title == "Second"
        assert remaining[1].title == "Third"

    def test_delete_last_ticket(self):
        """Should delete last ticket in list."""
        tickets = setup_tickets([
            {"title": "First"},
            {"title": "Second"},
            {"title": "Last to Delete"},
        ])

        run_cli_delete(tickets[2].id)

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        remaining = ticket_service.get_all()

        assert len(remaining) == 2
        assert remaining[0].title == "First"
        assert remaining[1].title == "Second"

    def test_delete_middle_ticket(self):
        """Should delete middle ticket in list."""
        tickets = setup_tickets([
            {"title": "First"},
            {"title": "Middle to Delete"},
            {"title": "Last"},
        ])

        run_cli_delete(tickets[1].id)

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        remaining = ticket_service.get_all()

        assert len(remaining) == 2
        assert remaining[0].title == "First"
        assert remaining[1].title == "Last"

    def test_delete_nonexistent_ticket_fails(self):
        """Should fail when ticket doesn't exist."""
        TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")

        fake_uuid = UUID("00000000-0000-0000-0000-000000000000")
        result = run_cli_delete(fake_uuid)

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_delete_already_deleted_ticket_fails(self):
        """Should fail when deleting already deleted ticket."""
        tickets = setup_tickets([
            {"title": "Task"},
        ])

        ticket_id = tickets[0].id

        # Delete once
        result1 = run_cli_delete(ticket_id)
        assert result1.returncode == 0

        # Try to delete again
        result2 = run_cli_delete(ticket_id)
        assert result2.returncode != 0

    def test_delete_displays_success_message(self):
        """Should display success message after deletion."""
        tickets = setup_tickets([
            {"title": "Task"},
        ])

        result = run_cli_delete(tickets[0].id)

        assert result.returncode == 0
        assert "deleted" in result.stdout.lower() or "removed" in result.stdout.lower() or "success" in result.stdout.lower()

    def test_delete_invalid_uuid_format_fails(self):
        """Should fail with invalid UUID format."""
        result = run_cli_delete("not-a-uuid")

        assert result.returncode != 0

    def test_delete_multiple_tickets_sequentially(self):
        """Should handle deleting multiple tickets one by one."""
        tickets = setup_tickets([
            {"title": "Task 1"},
            {"title": "Task 2"},
            {"title": "Task 3"},
        ])

        # Delete all three
        result1 = run_cli_delete(tickets[0].id)
        result2 = run_cli_delete(tickets[1].id)
        result3 = run_cli_delete(tickets[2].id)

        assert result1.returncode == 0
        assert result2.returncode == 0
        assert result3.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        remaining = ticket_service.get_all()

        assert len(remaining) == 0

    def test_delete_closed_ticket(self):
        """Should delete closed ticket."""
        tickets = setup_tickets([
            {"title": "Closed Task", "status": "closed"},
        ])

        result = run_cli_delete(tickets[0].id)

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        assert ticket_service.get_by_id(tickets[0].id) is None

    def test_delete_open_ticket(self):
        """Should delete open ticket."""
        tickets = setup_tickets([
            {"title": "Open Task", "status": "open"},
        ])

        result = run_cli_delete(tickets[0].id)

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        assert ticket_service.get_by_id(tickets[0].id) is None

    def test_delete_high_priority_ticket(self):
        """Should delete high priority ticket."""
        tickets = setup_tickets([
            {"title": "Important Task", "priority": "high"},
        ])

        result = run_cli_delete(tickets[0].id)

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        assert ticket_service.get_by_id(tickets[0].id) is None

    def test_delete_ticket_with_tags(self):
        """Should delete ticket even if it has tags."""
        tickets = setup_tickets([
            {"title": "Tagged Task", "tags": ["bug", "urgent", "backend"]},
        ])

        result = run_cli_delete(tickets[0].id)

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        assert ticket_service.get_by_id(tickets[0].id) is None

    def test_delete_ticket_with_long_description(self):
        """Should delete ticket with long description."""
        long_desc = "This is a very long description. " * 50
        tickets = setup_tickets([
            {"title": "Complex Task", "description": long_desc},
        ])

        result = run_cli_delete(tickets[0].id)

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        assert ticket_service.get_by_id(tickets[0].id) is None

    def test_delete_preserves_file_structure(self):
        """Should maintain valid JSON structure after deletion."""
        tickets = setup_tickets([
            {"title": "Task 1"},
            {"title": "Task 2"},
        ])

        run_cli_delete(tickets[0].id)

        # Verify file is still valid JSON
        import json
        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Task 2"
