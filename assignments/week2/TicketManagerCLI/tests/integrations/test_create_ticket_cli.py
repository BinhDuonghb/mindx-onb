import subprocess
import sys
from uuid import UUID

from ticket_manager.config import TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.services.ticketService import TicketService


def run_cli_create(**kwargs) -> subprocess.CompletedProcess:
    """Helper to run create command with given arguments."""
    cmd = [sys.executable, "main.py", "create"]

    for key, value in kwargs.items():
        if value is not None:
            cmd.append(f"--{key}")
            cmd.append(str(value))

    return subprocess.run(cmd, capture_output=True, text=True)


class TestCreateTicketCLI:
    """Test the create ticket CLI command."""

    def test_create_ticket_happy_path(self):
        """Should create ticket with all arguments provided."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Fix login bug",
            description="Login returns 500",
            priority="high",
            tags="bug,backend",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert TICKETS_FILE.exists()

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert len(tickets) == 1
        ticket = tickets[0]

        assert ticket.id is not None
        assert isinstance(ticket.id, UUID)
        assert ticket.title == "Fix login bug"
        assert ticket.description == "Login returns 500"
        assert ticket.priority == "high"
        assert ticket.status == "open"
        assert ticket.tags == ["bug", "backend"]

    def test_create_ticket_with_required_fields_only(self):
        """Should create ticket with only required title field."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(title="Simple Task")

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert len(tickets) == 1
        ticket = tickets[0]

        assert ticket.title == "Simple Task"
        assert ticket.description == ""
        assert ticket.priority == "medium"  # Default priority
        assert ticket.status == "open"
        assert ticket.tags == []

    def test_create_ticket_without_title_fails(self):
        """Should fail when title is not provided."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(description="Missing title")

        assert result.returncode != 0
        assert "required" in result.stdout.lower()

        # Verify no ticket was created
        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()
        assert len(tickets) == 0

    def test_create_ticket_with_low_priority(self):
        """Should create ticket with low priority."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Nice to have feature",
            priority="low"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].priority == "low"

    def test_create_ticket_with_default_priority(self):
        """Should use medium priority when not specified."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(title="Medium Priority Task")

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].priority == "medium"

    def test_create_ticket_with_invalid_priority_fails(self):
        """Should fail with invalid priority value."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Task",
            priority="critical"  # Invalid priority
        )

        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower() or "critical" in result.stderr.lower()

    def test_create_ticket_with_empty_tags(self):
        """Should create ticket with empty tags string."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="No Tags Task",
            tags=""
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].tags == []

    def test_create_ticket_with_single_tag(self):
        """Should create ticket with a single tag."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Single Tag Task",
            tags="urgent"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].tags == ["urgent"]

    def test_create_ticket_with_multiple_tags(self):
        """Should parse multiple comma-separated tags correctly."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Multi Tag Task",
            tags="bug,feature,urgent,backend"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].tags == ["bug", "feature", "urgent", "backend"]

    def test_create_ticket_with_tags_with_spaces(self):
        """Should trim whitespace from tags."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Spaced Tags",
            tags="bug , frontend , urgent"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        # Should have trimmed spaces
        assert tickets[0].tags == ["bug", "frontend", "urgent"]

    def test_create_multiple_tickets(self):
        """Should create multiple tickets with unique IDs."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result1 = run_cli_create(title="First Task")
        result2 = run_cli_create(title="Second Task")
        result3 = run_cli_create(title="Third Task")

        assert result1.returncode == 0
        assert result2.returncode == 0
        assert result3.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert len(tickets) == 3
        assert tickets[0].title == "First Task"
        assert tickets[1].title == "Second Task"
        assert tickets[2].title == "Third Task"

        # Verify all IDs are unique
        ids = [t.id for t in tickets]
        assert len(ids) == len(set(ids))

    def test_create_ticket_with_special_characters(self):
        """Should handle special characters in title and description."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Fix: API response [500] error!",
            description="User can't login - please fix ASAP (critical bug)"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        ticket = tickets[0]
        assert ticket.title == "Fix: API response [500] error!"
        assert ticket.description == "User can't login - please fix ASAP (critical bug)"

    def test_create_ticket_outputs_success_message(self):
        """Should print success message with ticket ID."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(title="Test Task")

        assert result.returncode == 0
        assert "created successfully" in result.stdout.lower()
        assert "id:" in result.stdout.lower()

    def test_create_ticket_default_status_is_open(self):
        """Should set status to 'open' by default."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(title="New Task")

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].status == "open"

    def test_create_ticket_with_long_description(self):
        """Should handle long descriptions."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        long_description = "This is a very long description. " * 20
        result = run_cli_create(
            title="Complex Task",
            description=long_description
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].description == long_description

    def test_create_ticket_with_creator_email(self):
        """Should create ticket with creator email."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Task with Creator",
            creator="dev@example.com"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].creator == "dev@example.com"

    def test_create_ticket_with_assignee_email(self):
        """Should create ticket with assignee email."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Task with Assignee",
            assignee="qa@example.com"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].assignee == "qa@example.com"

    def test_create_ticket_with_estimated_time(self):
        """Should create ticket with estimated time."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Task with Time Estimate",
            estimated_time="5.5"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        assert tickets[0].estimated_time == 5.5

    def test_create_ticket_with_all_new_fields(self):
        """Should create ticket with creator, assignee, and estimated_time."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Full Task",
            description="Complete task",
            priority="high",
            tags="feature,backend",
            creator="dev@example.com",
            assignee="qa@example.com",
            estimated_time="8.5"
        )

        assert result.returncode == 0

        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()

        ticket = tickets[0]
        assert ticket.title == "Full Task"
        assert ticket.description == "Complete task"
        assert ticket.priority == "high"
        assert ticket.tags == ["feature", "backend"]
        assert ticket.creator == "dev@example.com"
        assert ticket.assignee == "qa@example.com"
        assert ticket.estimated_time == 8.5

    def test_create_ticket_with_invalid_creator_email_fails(self):
        """Should fail when creator email is invalid."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Task",
            creator="not-an-email"
        )

        assert result.returncode != 0
        assert "error" in result.stdout.lower() or "invalid" in result.stdout.lower()

        # Verify no ticket was created
        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()
        assert len(tickets) == 0

    def test_create_ticket_with_invalid_assignee_email_fails(self):
        """Should fail when assignee email is invalid."""
        TICKETS_FILE.write_text("[]", encoding="utf-8")

        result = run_cli_create(
            title="Task",
            assignee="user@.invalid.com"
        )

        assert result.returncode != 0
        assert "error" in result.stdout.lower() or "invalid" in result.stdout.lower()

        # Verify no ticket was created
        db_client = DBClient(TICKETS_FILE)
        ticket_service = TicketService(db_client)
        tickets = ticket_service.get_all()
        assert len(tickets) == 0

