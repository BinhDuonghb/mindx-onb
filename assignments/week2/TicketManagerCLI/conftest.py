"""Root conftest.py for pytest configuration and shared fixtures."""
import os
import sys
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def use_temp_test_database(tmp_path, monkeypatch):
    """
    Automatically use a temporary directory for test database.

    This fixture:
    - Ensures each test runs in isolation
    - Prevents test_tickets.json from being modified in git
    - Cleans up automatically after each test

    Scope: function (runs for every test)
    """
    # Get the test data file path
    from ticket_manager.config import TEST_TICKETS_FILE

    # Create a temporary test database file in tmp_path
    temp_test_db = tmp_path / "test_tickets.json"
    temp_test_db.write_text("[]", encoding="utf-8")

    # Monkeypatch the TEST_TICKETS_FILE to point to our temporary file
    monkeypatch.setattr(
        "ticket_manager.config.TEST_TICKETS_FILE",
        temp_test_db
    )

    # Also patch it in data.db_client if it's imported there
    try:
        import data.db_client
        if hasattr(data.db_client, "TEST_TICKETS_FILE"):
            monkeypatch.setattr(
                "data.db_client.TEST_TICKETS_FILE",
                temp_test_db
            )
    except (ImportError, AttributeError):
        pass

    # Patch it in any subprocess calls by setting environment variable
    monkeypatch.setenv("PYTEST_TEMP_TEST_DB", str(temp_test_db))

    yield temp_test_db

    # Cleanup happens automatically when tmp_path is destroyed
