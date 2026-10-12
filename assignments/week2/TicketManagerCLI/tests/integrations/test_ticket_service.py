import pytest
from uuid import UUID
from ticket_manager.config import TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.services.ticketService import TicketService


@pytest.fixture
def db_client():
    """Initialize DBClient with fresh storage for each test."""
    TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")
    return DBClient(TEST_TICKETS_FILE)


@pytest.fixture
def ticket_service(db_client):
    """Initialize TicketService with a clean DBClient."""
    return TicketService(db_client)


@pytest.fixture(autouse=True)
def cleanup_tickets_file():
    """Ensure tickets file is clean before each test."""
    TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")
    yield
    # Don't reset after to allow data persistence inspection


class TestTicketServiceCreate:
    """Test ticket creation."""

    def test_create_ticket_with_required_fields_only(self, ticket_service: TicketService):
        """Should create ticket with only required title field."""
        ticket = Ticket(id=None, title="New Task")
        created = ticket_service.create(ticket)

        assert created.id is not None
        assert isinstance(created.id, UUID)
        assert created.title == "New Task"
        assert created.status == "open"
        assert created.priority == "medium"
        assert created.tags == []

    def test_create_ticket_with_all_fields(self, ticket_service: TicketService):
        """Should create ticket with all fields specified."""
        ticket = Ticket(
            id=None,
            title="Bug Fix",
            description="Fix login issue",
            status="open",
            priority="high",
            tags=["bug", "urgent"],
        )
        created = ticket_service.create(ticket)

        assert created.id is not None
        assert isinstance(created.id, UUID)
        assert created.title == "Bug Fix"
        assert created.description == "Fix login issue"
        assert created.priority == "high"
        assert created.tags == ["bug", "urgent"]

    def test_create_multiple_tickets_generates_unique_uuids(self, ticket_service: TicketService):
        """Should generate unique UUIDs for multiple tickets."""
        ticket1 = Ticket(id=None, title="First")
        ticket2 = Ticket(id=None, title="Second")
        ticket3 = Ticket(id=None, title="Third")

        created1 = ticket_service.create(ticket1)
        created2 = ticket_service.create(ticket2)
        created3 = ticket_service.create(ticket3)

        assert created1.id != created2.id
        assert created2.id != created3.id
        assert created1.id != created3.id

    def test_create_ticket_without_title_raises_error(self, ticket_service: TicketService):
        """Should raise error when title is empty."""
        ticket = Ticket(id=None, title="")

        with pytest.raises(ValueError, match="Ticket title is required"):
            ticket_service.create(ticket)

    def test_create_ticket_persists_to_db(self, ticket_service, db_client):
        """Should persist created ticket to database."""
        ticket = Ticket(id=None, title="Persistent Ticket", priority="high")
        created = ticket_service.create(ticket)

        # Verify by reading directly from db
        tickets_data = db_client.read()
        assert len(tickets_data) == 1
        assert tickets_data[0]["title"] == "Persistent Ticket"
        assert tickets_data[0]["priority"] == "high"
        assert UUID(tickets_data[0]["id"]) == created.id


class TestTicketServiceRead:
    """Test reading tickets."""

    def test_get_all_returns_empty_list(self, ticket_service: TicketService):
        """Should return empty list when no tickets exist."""
        tickets = ticket_service.get_all()
        assert tickets == []

    def test_get_all_returns_all_tickets(self, ticket_service: TicketService):
        """Should return all created tickets."""
        ticket1 = Ticket(id=None, title="Task 1")
        ticket2 = Ticket(id=None, title="Task 2")
        ticket3 = Ticket(id=None, title="Task 3")

        ticket_service.create(ticket1)
        ticket_service.create(ticket2)
        ticket_service.create(ticket3)

        tickets = ticket_service.get_all()
        assert len(tickets) == 3
        assert tickets[0].title == "Task 1"
        assert tickets[1].title == "Task 2"
        assert tickets[2].title == "Task 3"

    def test_get_by_id_returns_ticket(self, ticket_service: TicketService):
        """Should return ticket with matching UUID."""
        ticket = Ticket(id=None, title="Target Ticket", priority="high")
        created = ticket_service.create(ticket)

        retrieved = ticket_service.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Target Ticket"
        assert retrieved.priority == "high"

    def test_get_by_id_returns_none_for_nonexistent(self, ticket_service: TicketService):
        """Should return None when ticket not found."""
        ticket = Ticket(id=None, title="Single Ticket")
        ticket_service.create(ticket)

        from uuid import uuid4
        fake_uuid = uuid4()
        retrieved = ticket_service.get_by_id(fake_uuid)
        assert retrieved is None

    def test_get_by_status_filters_correctly(self, ticket_service: TicketService):
        """Should return only tickets with matching status."""
        ticket_service.create(Ticket(id=None, title="Open Task", status="open"))
        ticket_service.create(Ticket(id=None, title="Closed Task", status="closed"))
        ticket_service.create(Ticket(id=None, title="Another Open", status="open"))

        open_tickets = ticket_service.get_by_status("open")
        assert len(open_tickets) == 2
        assert all(t.status == "open" for t in open_tickets)

    def test_get_by_priority_filters_correctly(self, ticket_service: TicketService):
        """Should return only tickets with matching priority."""
        ticket_service.create(Ticket(id=None, title="Low", priority="low"))
        ticket_service.create(Ticket(id=None, title="High", priority="high"))
        ticket_service.create(Ticket(id=None, title="Another High", priority="high"))

        high_tickets = ticket_service.get_by_priority("high")
        assert len(high_tickets) == 2
        assert all(t.priority == "high" for t in high_tickets)


class TestTicketServiceUpdate:
    """Test updating tickets."""

    def test_update_ticket_title(self, ticket_service: TicketService):
        """Should update ticket title."""
        ticket = Ticket(id=None, title="Original Title")
        created = ticket_service.create(ticket)

        updated = ticket_service.update(created.id, title="Updated Title")

        assert updated.title == "Updated Title"
        retrieved = ticket_service.get_by_id(created.id)
        assert retrieved.title == "Updated Title"

    def test_update_ticket_status(self, ticket_service: TicketService):
        """Should update ticket status."""
        ticket = Ticket(id=None, title="Task", status="open")
        created = ticket_service.create(ticket)

        updated = ticket_service.update(created.id, status="closed")

        assert updated.status == "closed"
        retrieved = ticket_service.get_by_id(created.id)
        assert retrieved.status == "closed"

    def test_update_multiple_fields(self, ticket_service: TicketService):
        """Should update multiple fields at once."""
        ticket = Ticket(id=None, title="Original", priority="low", status="open")
        created = ticket_service.create(ticket)

        updated = ticket_service.update(
            created.id,
            title="Updated",
            priority="high",
            status="closed",
            description="New description",
        )

        assert updated.title == "Updated"
        assert updated.priority == "high"
        assert updated.status == "closed"
        assert updated.description == "New description"

    def test_update_tags(self, ticket_service: TicketService):
        """Should update ticket tags."""
        ticket = Ticket(id=None, title="Task", tags=["old"])
        created = ticket_service.create(ticket)

        updated = ticket_service.update(created.id, tags=["new", "tag"])

        assert updated.tags == ["new", "tag"]

    def test_update_nonexistent_ticket_raises_error(self, ticket_service: TicketService):
        """Should raise error when updating non-existent ticket."""
        from uuid import uuid4
        fake_uuid = uuid4()
        with pytest.raises(ValueError, match="Ticket with id"):
            ticket_service.update(fake_uuid, title="New Title")

    def test_update_with_no_fields_raises_error(self, ticket_service: TicketService):
        """Should raise error when no fields provided."""
        ticket = Ticket(id=None, title="Task")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError, match="At least one field must be provided"):
            ticket_service.update(created.id)

    def test_update_with_invalid_field_raises_error(self, ticket_service: TicketService):
        """Should raise error for invalid field names."""
        ticket = Ticket(id=None, title="Task")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError, match="Invalid fields"):
            ticket_service.update(created.id, invalid_field="value")

    def test_update_preserves_other_fields(self, ticket_service: TicketService):
        """Should preserve fields not being updated."""
        ticket = Ticket(
            id=None,
            title="Original",
            description="Original description",
            priority="high",
            tags=["tag1"],
        )
        created = ticket_service.create(ticket)

        updated = ticket_service.update(created.id, title="New Title")

        assert updated.description == "Original description"
        assert updated.priority == "high"
        assert updated.tags == ["tag1"]


class TestTicketServiceDelete:
    """Test deleting tickets."""

    def test_delete_ticket_by_id(self, ticket_service: TicketService):
        """Should delete ticket with matching UUID."""
        ticket1 = Ticket(id=None, title="Keep This")
        ticket2 = Ticket(id=None, title="Delete This")
        ticket3 = Ticket(id=None, title="Keep This Too")

        created1 = ticket_service.create(ticket1)
        created2 = ticket_service.create(ticket2)
        created3 = ticket_service.create(ticket3)

        ticket_service.delete(created2.id)

        remaining = ticket_service.get_all()
        assert len(remaining) == 2
        assert all(t.id != created2.id for t in remaining)

    def test_delete_nonexistent_ticket_raises_error(self, ticket_service: TicketService):
        """Should raise error when deleting non-existent ticket."""
        from uuid import uuid4
        fake_uuid = uuid4()
        with pytest.raises(ValueError):
            ticket_service.delete(fake_uuid)

    def test_delete_last_ticket_leaves_empty(self, ticket_service: TicketService):
        """Should leave empty list after deleting last ticket."""
        ticket = Ticket(id=None, title="Only Ticket")
        created = ticket_service.create(ticket)

        ticket_service.delete(created.id)

        tickets = ticket_service.get_all()
        assert tickets == []


class TestTicketServiceValidation:
    """Test validation in ticket service."""

    def test_create_with_invalid_title_too_short(self, ticket_service: TicketService):
        """Should raise error for title shorter than 3 characters."""
        ticket = Ticket(id=None, title="ab")  # Too short

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_title_too_long(self, ticket_service: TicketService):
        """Should raise error for title longer than 255 characters."""
        ticket = Ticket(id=None, title="a" * 256)  # Too long

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_description_too_long(self, ticket_service: TicketService):
        """Should raise error for description longer than 5000 characters."""
        ticket = Ticket(id=None, title="Valid Title", description="a" * 5001)

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_priority(self, ticket_service: TicketService):
        """Should raise error for invalid priority."""
        ticket = Ticket(id=None, title="Valid Title", priority="critical")  # Invalid

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_status(self, ticket_service: TicketService):
        """Should raise error for invalid status."""
        ticket = Ticket(id=None, title="Valid Title", status="pending")  # Invalid

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_tag_too_short(self, ticket_service: TicketService):
        """Should raise error for tag shorter than 2 characters."""
        ticket = Ticket(id=None, title="Valid Title", tags=["a"])  # Too short

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_tag_too_long(self, ticket_service: TicketService):
        """Should raise error for tag longer than 50 characters."""
        ticket = Ticket(id=None, title="Valid Title", tags=["a" * 51])  # Too long

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_too_many_tags(self, ticket_service: TicketService):
        """Should raise error when more than 10 tags."""
        ticket = Ticket(
            id=None,
            title="Valid Title",
            tags=[f"tag{i}" for i in range(11)]  # 11 tags
        )

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_creator_email(self, ticket_service: TicketService):
        """Should raise error for invalid creator email."""
        ticket = Ticket(
            id=None,
            title="Valid Title",
            creator="not-an-email"  # Invalid email
        )

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_invalid_assignee_email(self, ticket_service: TicketService):
        """Should raise error for invalid assignee email."""
        ticket = Ticket(
            id=None,
            title="Valid Title",
            assignee="user@.invalid.com"  # Invalid email
        )

        with pytest.raises(ValueError):
            ticket_service.create(ticket)

    def test_create_with_valid_creator_email(self, ticket_service: TicketService):
        """Should create ticket with valid creator email."""
        ticket = Ticket(
            id=None,
            title="Valid Title",
            creator="dev@example.com"
        )

        created = ticket_service.create(ticket)
        assert created.creator == "dev@example.com"

    def test_create_with_valid_assignee_email(self, ticket_service: TicketService):
        """Should create ticket with valid assignee email."""
        ticket = Ticket(
            id=None,
            title="Valid Title",
            assignee="qa@example.com"
        )

        created = ticket_service.create(ticket)
        assert created.assignee == "qa@example.com"

    def test_create_with_valid_estimated_time(self, ticket_service: TicketService):
        """Should create ticket with valid estimated_time."""
        ticket = Ticket(
            id=None,
            title="Valid Title",
            estimated_time=5.5
        )

        created = ticket_service.create(ticket)
        assert created.estimated_time == 5.5

    def test_update_with_invalid_title(self, ticket_service: TicketService):
        """Should raise error when updating with invalid title."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError):
            ticket_service.update(created.id, title="a")  # Too short

    def test_update_with_invalid_description(self, ticket_service: TicketService):
        """Should raise error when updating with invalid description."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError):
            ticket_service.update(created.id, description="a" * 5001)  # Too long

    def test_update_with_invalid_priority(self, ticket_service: TicketService):
        """Should raise error when updating with invalid priority."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError):
            ticket_service.update(created.id, priority="invalid")

    def test_update_with_invalid_status(self, ticket_service: TicketService):
        """Should raise error when updating with invalid status."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError):
            ticket_service.update(created.id, status="invalid")

    def test_update_with_invalid_assignee_email(self, ticket_service: TicketService):
        """Should raise error when updating with invalid assignee email."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        with pytest.raises(ValueError):
            ticket_service.update(created.id, assignee="invalid-email")

    def test_update_with_valid_assignee_email(self, ticket_service: TicketService):
        """Should update ticket with valid assignee email."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        updated = ticket_service.update(created.id, assignee="new@example.com")
        assert updated.assignee == "new@example.com"

    def test_update_with_valid_estimated_time(self, ticket_service: TicketService):
        """Should update ticket with valid estimated_time."""
        ticket = Ticket(id=None, title="Valid Title")
        created = ticket_service.create(ticket)

        updated = ticket_service.update(created.id, estimated_time=3.5)
        assert updated.estimated_time == 3.5


class TestTicketServiceIntegration:
    """Integration tests combining multiple operations."""

    def test_create_update_read_workflow(self, ticket_service: TicketService):
        """Should handle complete create-update-read workflow."""
        # Create
        ticket = Ticket(
            id=None,
            title="New Feature",
            description="Implement user auth",
            priority="high",
        )
        created = ticket_service.create(ticket)

        # Update
        ticket_service.update(created.id, status="in-progress", priority="medium")

        # Read
        retrieved = ticket_service.get_by_id(created.id)

        assert retrieved.title == "New Feature"
        assert retrieved.status == "in-progress"
        assert retrieved.priority == "medium"
        assert retrieved.description == "Implement user auth"

    def test_multiple_crud_operations(self, ticket_service: TicketService):
        """Should handle multiple CRUD operations correctly."""
        # Create multiple
        tickets = [
            Ticket(id=None, title=f"Task {i}", priority="high" if i % 2 == 0 else "low")
            for i in range(5)
        ]
        created_ids = [ticket_service.create(t).id for t in tickets]

        # Filter by priority
        high_priority = ticket_service.get_by_priority("high")
        assert len(high_priority) == 3

        # Update some
        ticket_service.update(created_ids[0], status="closed")
        ticket_service.update(created_ids[1], status="in-progress")

        # Delete one
        ticket_service.delete(created_ids[2])

        # Verify final state
        remaining = ticket_service.get_all()
        assert len(remaining) == 4
        assert remaining[0].status == "closed"
        assert remaining[1].status == "in-progress"

    def test_persistence_across_service_instances(self, db_client):
        """Should persist data across different service instances."""
        # Create with first service instance
        service1 = TicketService(db_client)
        ticket = Ticket(id=None, title="Persistent Task", priority="high")
        created = service1.create(ticket)

        # Read with second service instance
        service2 = TicketService(db_client)
        retrieved = service2.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.title == "Persistent Task"
        assert retrieved.priority == "high"
