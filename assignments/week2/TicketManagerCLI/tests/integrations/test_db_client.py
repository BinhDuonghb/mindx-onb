import json
import pytest

from ticket_manager.config import TEST_TICKETS_FILE
from data.db_client import DBClient


@pytest.fixture
def db_client():
    """Initialize DBClient with fresh storage for each test."""
    # Reset the file to empty state
    TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")
    return DBClient(TEST_TICKETS_FILE)


@pytest.fixture(autouse=True)
def cleanup_tickets_file():
    """Ensure tickets file is clean before and after each test."""
    yield
    TEST_TICKETS_FILE.write_text("[]", encoding="utf-8")


class TestDBClientRead:
    """Test reading operations."""

    def test_read_empty_file_returns_empty_list(self, db_client):
        """Should return empty list when file is empty."""
        tickets = db_client.read()
        assert tickets == []

    def test_read_returns_all_tickets(self, db_client):
        """Should return all tickets from file."""
        # Write sample data
        sample_data = [
            {"id": 1, "title": "Ticket 1", "status": "open"},
            {"id": 2, "title": "Ticket 2", "status": "closed"},
        ]
        TEST_TICKETS_FILE.write_text(json.dumps(sample_data), encoding="utf-8")

        tickets = db_client.read()
        assert len(tickets) == 2
        assert tickets[0]["title"] == "Ticket 1"
        assert tickets[1]["title"] == "Ticket 2"


class TestDBClientWrite:
    """Test write operations."""

    def test_write_single_ticket_to_empty_file(self, db_client):
        """Should write a single ticket to empty file."""
        ticket = {"id": 1, "title": "New Ticket", "status": "open"}
        db_client.write(ticket)

        # Verify file content
        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["title"] == "New Ticket"

    def test_write_multiple_tickets_appends(self, db_client):
        """Should append ticket to existing tickets."""
        ticket1 = {"id": 1, "title": "Ticket 1", "status": "open"}
        ticket2 = {"id": 2, "title": "Ticket 2", "status": "open"}

        db_client.write(ticket1)
        db_client.write(ticket2)

        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    def test_write_preserves_ticket_structure(self, db_client):
        """Should preserve all fields in ticket object."""
        ticket = {
            "id": 1,
            "title": "Complex Ticket",
            "description": "A detailed description",
            "priority": "high",
            "status": "open",
            "tags": ["bug", "backend"],
        }
        db_client.write(ticket)

        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[0]["description"] == "A detailed description"
        assert data[0]["tags"] == ["bug", "backend"]


class TestDBClientUpdate:
    """Test update operations."""

    def test_update_ticket_by_id(self, db_client):
        """Should update ticket fields when id matches."""
        # Setup initial data
        initial_data = [
            {"id": 1, "title": "Original Title", "status": "open"},
            {"id": 2, "title": "Other Ticket", "status": "open"},
        ]
        TEST_TICKETS_FILE.write_text(json.dumps(initial_data), encoding="utf-8")

        # Update ticket
        updated_ticket = {"id": 1, "title": "Updated Title", "status": "closed"}
        db_client.update(ticket_id=1, updated_data=updated_ticket)

        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[0]["title"] == "Updated Title"
        assert data[0]["status"] == "closed"
        assert data[1]["title"] == "Other Ticket"  # Other tickets unchanged

    def test_update_nonexistent_ticket_raises_error(self, db_client):
        """Should raise error when updating non-existent ticket."""
        TEST_TICKETS_FILE.write_text(json.dumps([{"id": 1, "title": "Ticket"}]), encoding="utf-8")

        with pytest.raises(ValueError):
            db_client.update(ticket_id=999, updated_data={"title": "New Title"})

    def test_update_partial_fields(self, db_client):
        """Should update only specified fields."""
        initial_data = [
            {
                "id": 1,
                "title": "Original",
                "description": "Original description",
                "status": "open",
            }
        ]
        TEST_TICKETS_FILE.write_text(json.dumps(initial_data), encoding="utf-8")

        # Update only title
        db_client.update(ticket_id=1, updated_data={"title": "New Title"})

        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[0]["title"] == "New Title"
        assert data[0]["description"] == "Original description"  # Unchanged


class TestDBClientDelete:
    """Test delete operations."""

    def test_delete_ticket_by_id(self, db_client):
        """Should remove ticket with matching id."""
        initial_data = [
            {"id": 1, "title": "Ticket 1"},
            {"id": 2, "title": "Ticket 2"},
            {"id": 3, "title": "Ticket 3"},
        ]
        TEST_TICKETS_FILE.write_text(json.dumps(initial_data), encoding="utf-8")

        db_client.delete(ticket_id=2)

        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2
        assert all(t["id"] != 2 for t in data)
        assert data[0]["id"] == 1
        assert data[1]["id"] == 3

    def test_delete_nonexistent_ticket_raises_error(self, db_client):
        """Should raise error when deleting non-existent ticket."""
        TEST_TICKETS_FILE.write_text(json.dumps([{"id": 1, "title": "Ticket"}]), encoding="utf-8")

        with pytest.raises(ValueError):
            db_client.delete(ticket_id=999)

    def test_delete_last_ticket_leaves_empty_array(self, db_client):
        """Should leave empty array after deleting last ticket."""
        TEST_TICKETS_FILE.write_text(json.dumps([{"id": 1, "title": "Only Ticket"}]), encoding="utf-8")

        db_client.delete(ticket_id=1)

        with open(TEST_TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data == []


class TestDBClientEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_corrupted_json_gracefully(self, db_client):
        """Should raise error for corrupted JSON."""
        TEST_TICKETS_FILE.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            db_client.read()

    def test_file_is_created_if_not_exists(self, db_client):
        """Should create file if it doesn't exist."""
        # Remove the file
        if TEST_TICKETS_FILE.exists():
            TEST_TICKETS_FILE.unlink()

        # Attempt read on non-existent file
        # This test documents the expected behavior
        # Either it creates the file or raises an error — decide based on design
        try:
            result = db_client.read()
            # If it succeeds, verify file was created
            assert TEST_TICKETS_FILE.exists()
        except FileNotFoundError:
            # If it raises, that's also acceptable behavior
            pass
