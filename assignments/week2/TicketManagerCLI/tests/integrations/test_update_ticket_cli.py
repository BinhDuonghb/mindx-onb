import subprocess
import sys
from uuid import UUID

from ticket_manager.config import TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.services.ticketService import TicketService


def run_cli_update(ticket_id, **kwargs) -> subprocess.CompletedProcess:
    """Helper to run update command with given arguments."""
    cmd = [sys.executable, "main.py", "--test", "update", str(ticket_id)]

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


class TestUpdateTicketCLI:
    """Test the update ticket CLI command."""

    def test_update_ticket_status_to_closed(self):
        """Should update ticket status to closed."""
        tickets = setup_tickets([
            {"title": "Task to Close", "status": "open"},
        ])

        ticket_id = tickets[0].id
        result = run_cli_update(ticket_id, status="closed")

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        updated = ticket_service.get_by_id(ticket_id)

        assert updated.status == "closed"
        assert updated.title == "Task to Close"  # Other fields unchanged

    def test_update_ticket_status_to_in_progress(self):
        """Should update ticket status to in-progress."""
        tickets = setup_tickets([
            {"title": "Task", "status": "open"},
        ])

        result = run_cli_update(tickets[0].id, status="in-progress")

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        updated = ticket_service.get_by_id(tickets[0].id)

        assert updated.status == "in-progress"

    def test_update_ticket_status_from_closed_to_open(self):
        """Should reopen closed ticket."""
        tickets = setup_tickets([
            {"title": "Reopened Task", "status": "closed"},
        ])

        result = run_cli_update(tickets[0].id, status="open")

        assert result.returncode == 0

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        updated = ticket_service.get_by_id(tickets[0].id)

        assert updated.status == "open"

    def test_update_nonexistent_ticket_fails(self):
        """Should fail when ticket doesn't exist."""
        TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")

        fake_uuid = UUID("00000000-0000-0000-0000-000000000000")
        result = run_cli_update(fake_uuid, status="closed")

        assert result.returncode != 0

    def test_update_without_status_fails(self):
        """Should fail when status is not provided."""
        tickets = setup_tickets([
            {"title": "Task"},
        ])

        result = run_cli_update(tickets[0].id)

        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "status" in result.stderr.lower()

    def test_update_with_invalid_status_fails(self):
        """Should fail with invalid status value."""
        tickets = setup_tickets([
            {"title": "Task"},
        ])

        result = run_cli_update(tickets[0].id, status="invalid-status")

        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower() or "invalid-status" in result.stderr.lower()

    def test_update_displays_success_message(self):
        """Should display success message after update."""
        tickets = setup_tickets([
            {"title": "Task"},
        ])

        result = run_cli_update(tickets[0].id, status="closed")

        assert result.returncode == 0
        assert "updated" in result.stdout.lower() or "success" in result.stdout.lower()

    def test_update_multiple_tickets_independently(self):
        """Should update only the specified ticket."""
        tickets = setup_tickets([
            {"title": "Task 1", "status": "open"},
            {"title": "Task 2", "status": "open"},
            {"title": "Task 3", "status": "open"},
        ])

        run_cli_update(tickets[0].id, status="closed")

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)

        assert ticket_service.get_by_id(tickets[0].id).status == "closed"
        assert ticket_service.get_by_id(tickets[1].id).status == "open"
        assert ticket_service.get_by_id(tickets[2].id).status == "open"

    def test_update_preserves_other_fields(self):
        """Should preserve other fields when updating status."""
        tickets = setup_tickets([
            {
                "title": "Important Task",
                "description": "Must be done",
                "priority": "high",
                "tags": ["urgent"],
                "status": "open",
            },
        ])

        run_cli_update(tickets[0].id, status="closed")

        db_client = DBClient(TEST_TICKETS_FILE)
        ticket_service = TicketService(db_client)
        updated = ticket_service.get_by_id(tickets[0].id)

        assert updated.title == "Important Task"
        assert updated.description == "Must be done"
        assert updated.priority == "high"
        assert updated.tags == ["urgent"]
        assert updated.status == "closed"

    def test_update_invalid_uuid_format_fails(self):
        """Should fail with invalid UUID format."""
        result = run_cli_update("not-a-uuid", status="closed")

        assert result.returncode != 0

    def test_update_valid_status_transitions(self):
        """Should allow all valid status transitions."""
        statuses = ["open", "in-progress", "closed"]

        for start_status in statuses:
            for end_status in statuses:
                if start_status != end_status:
                    tickets = setup_tickets([
                        {"title": f"Task {start_status} -> {end_status}", "status": start_status},
                    ])

                    result = run_cli_update(tickets[0].id, status=end_status)
                    assert result.returncode == 0

                    db_client = DBClient(TEST_TICKETS_FILE)
                    ticket_service = TicketService(db_client)
                    updated = ticket_service.get_by_id(tickets[0].id)
                    assert updated.status == end_status
