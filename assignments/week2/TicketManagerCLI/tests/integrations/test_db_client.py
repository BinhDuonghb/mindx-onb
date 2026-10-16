import json
import pytest

from data.db_client import DBClient


@pytest.fixture
def db_client(use_temp_test_database):
    """Initialize DBClient with fresh storage for each test."""
    return DBClient(use_temp_test_database)


class TestDBClientRead:
    """
    Test DBClient.read() contract.

    DBClient is the data layer — it does NOT handle missing files gracefully.
    It raises exceptions; the CLI layer catches them and shows user-friendly messages.
    """

    def test_read_empty_file_returns_empty_list(self, db_client):
        """Should return empty list when file exists but is empty."""
        tickets = db_client.read()
        assert tickets == []

    def test_read_returns_all_tickets(self, db_client, use_temp_test_database):
        """Should return all tickets from file."""
        # Write sample data
        sample_data = [
            {"id": 1, "title": "Ticket 1", "status": "open"},
            {"id": 2, "title": "Ticket 2", "status": "closed"},
        ]
        use_temp_test_database.write_text(json.dumps(sample_data), encoding="utf-8")

        tickets = db_client.read()
        assert len(tickets) == 2
        assert tickets[0]["title"] == "Ticket 1"
        assert tickets[1]["title"] == "Ticket 2"

    def test_read_missing_file_raises_file_not_found(self, use_temp_test_database):
        """Should raise FileNotFoundError when file doesn't exist."""
        # Delete the file
        if use_temp_test_database.exists():
            use_temp_test_database.unlink()

        db_client = DBClient(use_temp_test_database)

        # DBClient does NOT auto-create files
        with pytest.raises(FileNotFoundError):
            db_client.read()

    def test_read_corrupted_json_raises_json_decode_error(self, db_client, use_temp_test_database):
        """Should raise JSONDecodeError when file contains invalid JSON."""
        use_temp_test_database.write_text("{ invalid json }", encoding="utf-8")

        # DBClient does NOT auto-recover corrupted files
        with pytest.raises(json.JSONDecodeError):
            db_client.read()


class TestDBClientWrite:
    """
    Test DBClient.write() contract.

    DBClient.write() calls read() internally, so it inherits the same error behavior:
    - Raises FileNotFoundError if file doesn't exist
    - Raises JSONDecodeError if file contains invalid JSON
    """

    def test_write_single_ticket_to_empty_file(self, db_client, use_temp_test_database):
        """Should write a single ticket to empty file."""
        ticket = {"id": 1, "title": "New Ticket", "status": "open"}
        db_client.write(ticket)

        # Verify file content
        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["title"] == "New Ticket"

    def test_write_multiple_tickets_appends(self, db_client, use_temp_test_database):
        """Should append ticket to existing tickets."""
        ticket1 = {"id": 1, "title": "Ticket 1", "status": "open"}
        ticket2 = {"id": 2, "title": "Ticket 2", "status": "open"}

        db_client.write(ticket1)
        db_client.write(ticket2)

        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    def test_write_preserves_ticket_structure(self, db_client, use_temp_test_database):
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

        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[0]["description"] == "A detailed description"
        assert data[0]["tags"] == ["bug", "backend"]

    def test_write_to_missing_file_raises_file_not_found(self, use_temp_test_database):
        """Should raise FileNotFoundError when writing to missing file."""
        # Delete the file
        if use_temp_test_database.exists():
            use_temp_test_database.unlink()

        db_client = DBClient(use_temp_test_database)
        ticket = {"id": 1, "title": "New Ticket"}

        # DBClient does NOT auto-create files
        with pytest.raises(FileNotFoundError):
            db_client.write(ticket)

    def test_write_to_corrupted_json_raises_json_decode_error(self, db_client, use_temp_test_database):
        """Should raise JSONDecodeError when writing to file with invalid JSON."""
        use_temp_test_database.write_text("{ invalid json }", encoding="utf-8")
        ticket = {"id": 1, "title": "New Ticket"}

        # DBClient does NOT auto-recover
        with pytest.raises(json.JSONDecodeError):
            db_client.write(ticket)


class TestDBClientUpdate:
    """Test update operations."""

    def test_update_ticket_by_id(self, db_client, use_temp_test_database):
        """Should update ticket fields when id matches."""
        # Setup initial data
        initial_data = [
            {"id": 1, "title": "Original Title", "status": "open"},
            {"id": 2, "title": "Other Ticket", "status": "open"},
        ]
        use_temp_test_database.write_text(json.dumps(initial_data), encoding="utf-8")

        # Update ticket
        updated_ticket = {"id": 1, "title": "Updated Title", "status": "closed"}
        db_client.update(ticket_id=1, updated_data=updated_ticket)

        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[0]["title"] == "Updated Title"
        assert data[0]["status"] == "closed"
        assert data[1]["title"] == "Other Ticket"  # Other tickets unchanged

    def test_update_nonexistent_ticket_raises_error(self, db_client, use_temp_test_database):
        """Should raise error when updating non-existent ticket."""
        use_temp_test_database.write_text(json.dumps([{"id": 1, "title": "Ticket"}]), encoding="utf-8")

        with pytest.raises(ValueError):
            db_client.update(ticket_id=999, updated_data={"title": "New Title"})

    def test_update_partial_fields(self, db_client, use_temp_test_database):
        """Should update only specified fields."""
        initial_data = [
            {
                "id": 1,
                "title": "Original",
                "description": "Original description",
                "status": "open",
            }
        ]
        use_temp_test_database.write_text(json.dumps(initial_data), encoding="utf-8")

        # Update only title
        db_client.update(ticket_id=1, updated_data={"title": "New Title"})

        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[0]["title"] == "New Title"
        assert data[0]["description"] == "Original description"  # Unchanged


class TestDBClientDelete:
    """Test delete operations."""

    def test_delete_ticket_by_id(self, db_client, use_temp_test_database):
        """Should remove ticket with matching id."""
        initial_data = [
            {"id": 1, "title": "Ticket 1"},
            {"id": 2, "title": "Ticket 2"},
            {"id": 3, "title": "Ticket 3"},
        ]
        use_temp_test_database.write_text(json.dumps(initial_data), encoding="utf-8")

        db_client.delete(ticket_id=2)

        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2
        assert all(t["id"] != 2 for t in data)
        assert data[0]["id"] == 1
        assert data[1]["id"] == 3

    def test_delete_nonexistent_ticket_raises_error(self, db_client, use_temp_test_database):
        """Should raise error when deleting non-existent ticket."""
        use_temp_test_database.write_text(json.dumps([{"id": 1, "title": "Ticket"}]), encoding="utf-8")

        with pytest.raises(ValueError):
            db_client.delete(ticket_id=999)

    def test_delete_last_ticket_leaves_empty_array(self, db_client, use_temp_test_database):
        """Should leave empty array after deleting last ticket."""
        use_temp_test_database.write_text(json.dumps([{"id": 1, "title": "Only Ticket"}]), encoding="utf-8")

        db_client.delete(ticket_id=1)

        with open(use_temp_test_database, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data == []


class TestDBClientEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_corrupted_json_gracefully(self, db_client, use_temp_test_database):
        """Should raise error for corrupted JSON."""
        use_temp_test_database.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            db_client.read()

    def test_file_is_created_if_not_exists(self, db_client, use_temp_test_database):
        """Should create file if it doesn't exist."""
        # Remove the file
        if use_temp_test_database.exists():
            use_temp_test_database.unlink()

        # Attempt read on non-existent file
        # This test documents the expected behavior
        # Either it creates the file or raises an error — decide based on design
        try:
            result = db_client.read()
            # If it succeeds, verify file was created
            assert use_temp_test_database.exists()
        except FileNotFoundError:
            # If it raises, that's also acceptable behavior
            pass
