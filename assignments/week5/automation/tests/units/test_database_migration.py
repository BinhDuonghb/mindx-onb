"""Tests for database schema migration.

Reproduces legacy database issues and verifies migration fixes.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from srcs.models import AutomationState, AutomationStatus
from srcs.repositories.automation_state_repository import AutomationStateRepository


class TestDatabaseMigration:
    """Test schema migration for legacy databases."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        import os
        os.close(fd)
        yield Path(path)
        if Path(path).exists():
            try:
                Path(path).unlink()
            except:
                pass

    def create_legacy_db_missing_email_column(self, db_path: Path) -> None:
        """Create a legacy database without email_delivery_completed column."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Old schema without email_delivery_completed
            cursor.execute("""
                CREATE TABLE automation_state (
                    ticket_id INTEGER PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_decision TEXT,
                    last_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_checked_at TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at TEXT,
                    last_error TEXT,
                    reactivation_completed INTEGER NOT NULL DEFAULT 0,
                    odoo_note_completed INTEGER NOT NULL DEFAULT 0,
                    customer_response_completed INTEGER NOT NULL DEFAULT 0,
                    stage_update_completed INTEGER NOT NULL DEFAULT 0,
                    processing_lease_until TEXT
                )
            """)
            conn.commit()

    def create_legacy_db_missing_lease_token(self, db_path: Path) -> None:
        """Create a legacy database without lease_owner_token column."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Old schema without lease_owner_token or email_delivery_completed
            cursor.execute("""
                CREATE TABLE automation_state (
                    ticket_id INTEGER PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_decision TEXT,
                    last_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_checked_at TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at TEXT,
                    last_error TEXT,
                    reactivation_completed INTEGER NOT NULL DEFAULT 0,
                    odoo_note_completed INTEGER NOT NULL DEFAULT 0,
                    customer_response_completed INTEGER NOT NULL DEFAULT 0,
                    stage_update_completed INTEGER NOT NULL DEFAULT 0,
                    email_delivery_completed INTEGER NOT NULL DEFAULT 0,
                    processing_lease_until TEXT
                )
            """)
            conn.commit()

    def test_migrate_database_missing_email_column(self, temp_db):
        """Test migration when email_delivery_completed column is missing."""
        # Create legacy database without email column
        self.create_legacy_db_missing_email_column(temp_db)

        # Initialize repository (should trigger migration)
        repo = AutomationStateRepository(db_path=temp_db)

        # Verify email column now exists
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(automation_state)")
            columns = {row[1] for row in cursor.fetchall()}
            assert "email_delivery_completed" in columns

    def test_migrate_database_missing_lease_token(self, temp_db):
        """Test migration when lease_owner_token column is missing."""
        # Create legacy database without lease token
        self.create_legacy_db_missing_lease_token(temp_db)

        # Initialize repository (should trigger migration)
        repo = AutomationStateRepository(db_path=temp_db)

        # Verify lease_owner_token column now exists
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(automation_state)")
            columns = {row[1] for row in cursor.fetchall()}
            assert "lease_owner_token" in columns

    def test_migrate_legacy_database_preserves_data(self, temp_db):
        """Test that migration preserves existing data."""
        # Create legacy database
        self.create_legacy_db_missing_email_column(temp_db)

        # Insert test data
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO automation_state (
                    ticket_id, fingerprint, status, created_at, updated_at,
                    retry_count, reactivation_completed
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                100,
                "test_fp",
                AutomationStatus.PROCESSING.value,
                now.isoformat(),
                now.isoformat(),
                0,
                1
            ))
            conn.commit()

        # Migrate by initializing repository
        repo = AutomationStateRepository(db_path=temp_db)

        # Verify data is preserved
        state = repo.get(100)
        assert state is not None
        assert state.ticket_id == 100
        assert state.fingerprint == "test_fp"
        assert state.status == AutomationStatus.PROCESSING
        assert state.reactivation_completed is True

    def test_migration_is_idempotent(self, temp_db):
        """Test that migrations can run multiple times without error."""
        # Create legacy database
        self.create_legacy_db_missing_email_column(temp_db)

        # First migration
        repo1 = AutomationStateRepository(db_path=temp_db)

        # Verify columns exist after first migration
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(automation_state)")
            columns_after_first = {row[1] for row in cursor.fetchall()}

        # Second initialization (simulates running again)
        repo2 = AutomationStateRepository(db_path=temp_db)

        # Verify columns still exist and match
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(automation_state)")
            columns_after_second = {row[1] for row in cursor.fetchall()}

        assert columns_after_first == columns_after_second
        assert "email_delivery_completed" in columns_after_second
        assert "lease_owner_token" in columns_after_second

    def test_save_and_get_after_migration(self, temp_db):
        """Test save() and get() work correctly after migration."""
        # Create legacy database
        self.create_legacy_db_missing_email_column(temp_db)

        # Migrate
        repo = AutomationStateRepository(db_path=temp_db)

        # Create and save a new state
        state = AutomationState(
            ticket_id=200,
            fingerprint="test_fp_2",
            status=AutomationStatus.RETRY_SCHEDULED,
            reactivation_completed=True,
            email_delivery_completed=False,
        )

        # This should work after migration
        result = repo.save(state)
        assert result is True

        # Verify we can retrieve it
        retrieved = repo.get(200)
        assert retrieved is not None
        assert retrieved.ticket_id == 200
        assert retrieved.reactivation_completed is True
        assert retrieved.email_delivery_completed is False

    def test_reproduce_failure_without_migration(self, temp_db):
        """Reproduce the failure when migration is not applied."""
        # Create legacy database without email_delivery_completed
        self.create_legacy_db_missing_email_column(temp_db)

        # Insert legacy data
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO automation_state (
                    ticket_id, fingerprint, status, created_at, updated_at,
                    retry_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (1, "fp1", "processing", now.isoformat(), now.isoformat(), 0))
            conn.commit()

        # Try to save without migration - this would fail
        # But with migration, it should work
        repo = AutomationStateRepository(db_path=temp_db)

        state = AutomationState(
            ticket_id=2,
            fingerprint="fp2",
            status=AutomationStatus.PROCESSING,
        )

        # Should succeed after migration
        result = repo.save(state)
        assert result is True
