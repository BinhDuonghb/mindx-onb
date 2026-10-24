"""Tests for data safety when JSON is corrupt."""
import pytest
import json
from pathlib import Path

from KB.clients.mockKBClient import MockKBClient
from KB.models.document import Document


class TestCorruptJSONDataSafety:
    """Test that corrupt JSON files are preserved, not overwritten."""

    def test_corrupt_json_raises_error_not_silent(self, tmp_path):
        """Should raise ValueError for corrupt JSON instead of silently recovering."""
        persist_file = tmp_path / "corrupt.json"

        # Create a file with invalid JSON
        persist_file.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(ValueError, match="Persist file contains invalid JSON"):
            MockKBClient(persist_file=persist_file)

    def test_corrupt_json_file_is_not_overwritten(self, tmp_path):
        """Should NOT overwrite corrupt JSON file with sample data."""
        persist_file = tmp_path / "corrupt.json"
        corrupt_content = "{ invalid json }"

        # Create a file with invalid JSON
        persist_file.write_text(corrupt_content, encoding="utf-8")

        # Try to load it
        with pytest.raises(ValueError):
            MockKBClient(persist_file=persist_file)

        # Verify original file still has corrupt content (not overwritten)
        current_content = persist_file.read_text(encoding="utf-8")
        assert current_content == corrupt_content
        assert current_content != "["  # Not empty or overwritten

    def test_corrupt_json_file_backed_up(self, tmp_path):
        """Should create a .corrupt backup of the corrupt file."""
        persist_file = tmp_path / "data.json"
        corrupt_content = "{ this is not valid json: }"

        # Create a file with invalid JSON
        persist_file.write_text(corrupt_content, encoding="utf-8")

        # Try to load it
        with pytest.raises(ValueError):
            MockKBClient(persist_file=persist_file)

        # Verify backup file was created
        backup_file = Path(str(persist_file) + ".corrupt")
        assert backup_file.exists(), f"Backup file not found: {backup_file}"

        # Verify backup has the same corrupt content
        backup_content = backup_file.read_text(encoding="utf-8")
        assert backup_content == corrupt_content

    def test_error_message_indicates_backup_location(self, tmp_path):
        """Should provide clear error message with backup file location."""
        persist_file = tmp_path / "broken.json"
        persist_file.write_text("{ broken }", encoding="utf-8")

        with pytest.raises(ValueError) as exc_info:
            MockKBClient(persist_file=persist_file)

        error_msg = str(exc_info.value)
        assert "Persist file contains invalid JSON" in error_msg
        assert "backed up" in error_msg or "corrupt" in error_msg.lower()
        assert str(persist_file) in error_msg

    def test_corrupt_json_with_previously_added_data(self, tmp_path):
        """Should protect data that was previously added before corruption."""
        persist_file = tmp_path / "data.json"

        # Create initial client and add a document
        client1 = MockKBClient(persist_file=persist_file)
        doc = Document(
            id="doc-important",
            title="Important Data",
            content="This data must not be lost",
            node_path="/important",
            tags=["critical"]
        )
        client1.add(doc)

        # Verify it was saved
        saved_content = persist_file.read_text(encoding="utf-8")
        data = json.loads(saved_content)
        assert any(d["id"] == "doc-important" for d in data)

        # Now corrupt the file
        persist_file.write_text("{ corrupted: true }", encoding="utf-8")

        # Try to load corrupted file
        with pytest.raises(ValueError):
            MockKBClient(persist_file=persist_file)

        # Verify original file is NOT overwritten (still has corrupted content)
        assert persist_file.read_text(encoding="utf-8") == "{ corrupted: true }"

        # Verify backup has the corrupted content (not the original data)
        backup_file = Path(str(persist_file) + ".corrupt")
        assert backup_file.read_text(encoding="utf-8") == "{ corrupted: true }"

    def test_corrupt_json_prevents_data_loss_scenario(self, tmp_path):
        """Real scenario: prevent data loss when file gets corrupted."""
        persist_file = tmp_path / "kb_data.json"

        # Step 1: Create and populate KB with real data
        client = MockKBClient(persist_file=persist_file)

        # Add multiple documents
        for i in range(3):
            doc = Document(
                id=f"doc-{i}",
                title=f"Document {i}",
                content=f"Content for document {i}",
                node_path="/docs",
                tags=["doc"]
            )
            client.add(doc)

        # Verify data is saved
        saved_data = json.loads(persist_file.read_text(encoding="utf-8"))
        original_count = len(saved_data)
        assert original_count == 6  # 3 sample + 3 added

        # Step 2: Simulate file corruption (e.g., incomplete write)
        persist_file.write_text('{"incomplete": ', encoding="utf-8")

        # Step 3: Try to load - should fail safely
        with pytest.raises(ValueError, match="Persist file contains invalid JSON"):
            MockKBClient(persist_file=persist_file)

        # Step 4: Verify original file NOT overwritten
        current_content = persist_file.read_text(encoding="utf-8")
        assert current_content == '{"incomplete": '
        assert current_content != "["  # Not sample data

        # Step 5: Verify data can be recovered from backup
        backup_file = Path(str(persist_file) + ".corrupt")
        assert backup_file.exists()
        # User can manually restore from backup or contact admin
        # Data is NOT lost

    def test_nonexistent_file_still_initializes_normally(self, tmp_path):
        """Should still initialize with samples when file doesn't exist."""
        persist_file = tmp_path / "new_kb.json"

        # File doesn't exist yet
        assert not persist_file.exists()

        # Should create with samples
        client = MockKBClient(persist_file=persist_file)

        # Should have sample documents
        assert len(client._documents) == 3

        # File should now exist with sample data
        assert persist_file.exists()
        data = json.loads(persist_file.read_text(encoding="utf-8"))
        assert len(data) == 3

    def test_valid_json_loads_normally(self, tmp_path):
        """Should load valid JSON without error or backup creation."""
        persist_file = tmp_path / "valid.json"

        # Create valid JSON with documents
        valid_data = [
            {
                "id": "doc-001",
                "title": "Test",
                "content": "Content",
                "node_path": "/test",
                "tags": ["test"]
            }
        ]
        persist_file.write_text(json.dumps(valid_data), encoding="utf-8")

        # Load should work
        client = MockKBClient(persist_file=persist_file)

        # Should have loaded the document
        assert len(client._documents) == 1
        assert "doc-001" in client._documents

        # No backup should be created
        backup_file = Path(str(persist_file) + ".corrupt")
        assert not backup_file.exists()
