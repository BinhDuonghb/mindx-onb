"""AutomationStateRepository - SQLite persistence for automation processing state."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from srcs.services.gmail import CommunicationEvent

from srcs.models import AutomationState, AutomationStatus

logger = logging.getLogger(__name__)


class AutomationStateRepository:
    """Persistent repository for automation processing state using SQLite.

    Maintains a single state record per Odoo ticket, supporting:
    - Save and retrieve state
    - Atomic processing claims (prevent duplicate execution)
    - Recovery of stale PROCESSING records
    - Upsert operations
    - Transactional updates
    """

    def __init__(self, db_path: Path = Path("data/automation_state.db")):
        """Initialize repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema and apply migrations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS automation_state (
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
                        reactivation_authorized INTEGER NOT NULL DEFAULT 0,
                        odoo_note_completed INTEGER NOT NULL DEFAULT 0,
                        customer_response_completed INTEGER NOT NULL DEFAULT 0,
                        stage_update_completed INTEGER NOT NULL DEFAULT 0,
                        email_delivery_completed INTEGER NOT NULL DEFAULT 0,
                        processing_lease_until TEXT,
                        lease_owner_token TEXT,
                        ambiguous_write_outcome TEXT,
                        ambiguous_write_context TEXT
                    )
                """)

                # Create index on status for efficient queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status ON automation_state(status)
                """)

                # Create index on next_retry_at for efficient retry scheduling
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_next_retry_at ON automation_state(next_retry_at)
                """)

                # Communication events table - tracks which emails have been sent
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS communication_events (
                        ticket_id INTEGER NOT NULL,
                        event TEXT NOT NULL,
                        sent_at TEXT NOT NULL,
                        PRIMARY KEY (ticket_id, event)
                    )
                """)

                # Create index on ticket_id for efficient lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_comm_ticket ON communication_events(ticket_id)
                """)

                # Customer confirmation table - tracks when customer confirms resolution
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS customer_confirmations (
                        ticket_id INTEGER PRIMARY KEY,
                        confirmed_at TEXT NOT NULL
                    )
                """)

                conn.commit()

                # TASK 5 FIX: Apply schema migrations for legacy databases
                self._apply_migrations(conn)

                logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        """Apply schema migrations for legacy databases.

        TASK 5 FIX: Detect and migrate databases that don't have new columns.
        This allows the system to work with databases created by older versions.

        Handles:
        - email_delivery_completed: Track email delivery success separately (P1-03)
        - lease_owner_token: Ownership tokens for lease safety (TASK 3)
        - ambiguous_write_outcome: P2 Issue #5 unknown write tracking
        - ambiguous_write_context: P2 Issue #5 unknown write error context

        Args:
            conn: Active database connection

        Raises:
            Exception: If migration fails (wrapped for logging)
        """
        try:
            cursor = conn.cursor()

            # Get all existing columns
            cursor.execute("PRAGMA table_info(automation_state)")
            columns = {row[1] for row in cursor.fetchall()}

            # List of required columns with their definitions
            required_columns = {
                "email_delivery_completed": "INTEGER NOT NULL DEFAULT 0",
                "reactivation_authorized": "INTEGER NOT NULL DEFAULT 0",
                "lease_owner_token": "TEXT",
                "ambiguous_write_outcome": "TEXT",
                "ambiguous_write_context": "TEXT"
            }

            # Migrate any missing columns
            for column_name, column_def in required_columns.items():
                if column_name not in columns:
                    try:
                        logger.info(f"Migrating database: adding {column_name} column")
                        cursor.execute(f"""
                            ALTER TABLE automation_state
                            ADD COLUMN {column_name} {column_def}
                        """)
                        conn.commit()
                        logger.info(f"Migration complete: {column_name} column added")
                    except sqlite3.OperationalError as e:
                        # Column may already exist (race condition or previous attempt)
                        if "duplicate column name" in str(e):
                            logger.info(f"Column {column_name} already exists")
                        else:
                            raise

        except Exception as e:
            logger.error(f"Database migration failed: {str(e)}")
            raise  # Per Issue 1 requirement: Raise error if migration fails

    def get(self, ticket_id: int) -> Optional[AutomationState]:
        """Get automation state for a ticket.

        Args:
            ticket_id: Odoo ticket ID

        Returns:
            AutomationState or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM automation_state WHERE ticket_id = ?",
                    (ticket_id,)
                )
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_state(row)

        except Exception as e:
            logger.error(f"Failed to get state for ticket {ticket_id}: {str(e)}")
            return None

    def save(self, state: AutomationState, owner_token: Optional[str] = None) -> bool:
        """Save or update automation state (upsert).

        ISSUE #2 FINAL FIX 2: Rejects writes after lease expiration.

        If a record has a lease_owner_token (ownership is claimed), reject ANY write
        unless the supplied token matches and the lease is still active.

        Expired tokens cannot bypass protection. Missing tokens reject owned records.
        Unowned records can be created or updated via standard upsert.

        Args:
            state: AutomationState to save
            owner_token: Ownership token from claim_for_processing() - validates if record is owned

        Returns:
            True if successful, False if ownership validation fails
        """
        try:
            state.updated_at = datetime.now(timezone.utc)
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # FIX 2: Check if record exists and has ownership token
                cursor.execute("""
                    SELECT lease_owner_token, processing_lease_until
                    FROM automation_state
                    WHERE ticket_id = ?
                """, (state.ticket_id,))
                existing = cursor.fetchone()

                if existing:
                    stored_token, lease_until_str = existing

                    # FIX 2: If record has ownership token, validate it strictly
                    if stored_token is not None:
                        # Token exists - require exact match
                        if owner_token != stored_token:
                            logger.warning(
                                f"Token mismatch for ticket {state.ticket_id}: "
                                f"save rejected (expected token not provided or incorrect)"
                            )
                            return False

                        # FIX 2: Check lease expiration - even with correct token, reject if lease expired
                        if lease_until_str:
                            lease_until = datetime.fromisoformat(lease_until_str)
                            if now >= lease_until:
                                logger.warning(
                                    f"Lease expired for ticket {state.ticket_id}: "
                                    f"save rejected (token valid but lease no longer active)"
                                )
                                return False

                # FIX 2: If ownership is present, use atomic UPDATE with strict validation
                if existing and existing[0] is not None:
                    # Record is owned - use atomic UPDATE
                    cursor.execute("""
                        UPDATE automation_state
                        SET fingerprint = ?, status = ?, last_decision = ?, last_reason = ?,
                            updated_at = ?, last_checked_at = ?, retry_count = ?,
                            next_retry_at = ?, last_error = ?, reactivation_completed = ?,
                            reactivation_authorized = ?,
                            odoo_note_completed = ?, customer_response_completed = ?,
                            stage_update_completed = ?, email_delivery_completed = ?,
                            processing_lease_until = COALESCE(?, processing_lease_until),
                            ambiguous_write_outcome = ?, ambiguous_write_context = ?
                        WHERE ticket_id = ? AND lease_owner_token = ? AND
                              (processing_lease_until IS NULL OR processing_lease_until > ?)
                    """, (
                        state.fingerprint,
                        state.status.value,
                        state.last_decision,
                        state.last_reason,
                        state.updated_at.isoformat(),
                        state.last_checked_at.isoformat() if state.last_checked_at else None,
                        state.retry_count,
                        state.next_retry_at.isoformat() if state.next_retry_at else None,
                        state.last_error,
                        1 if state.reactivation_completed else 0,
                        1 if state.reactivation_authorized else 0,
                        1 if state.odoo_note_completed else 0,
                        1 if state.customer_response_completed else 0,
                        1 if state.stage_update_completed else 0,
                        1 if state.email_delivery_completed else 0,
                        state.processing_lease_until.isoformat() if state.processing_lease_until else None,
                        state.ambiguous_write_outcome,
                        state.ambiguous_write_context,
                        state.ticket_id,
                        owner_token,
                        now.isoformat()
                    ))

                    if cursor.rowcount == 0:
                        logger.warning(
                            f"Atomic validation failed for ticket {state.ticket_id}: "
                            f"save rejected"
                        )
                        return False
                else:
                    # No ownership or unowned record - use standard upsert
                    cursor.execute("""
                        INSERT INTO automation_state (
                            ticket_id, fingerprint, status, last_decision, last_reason,
                            created_at, updated_at, last_checked_at, retry_count,
                            next_retry_at, last_error, reactivation_completed, reactivation_authorized,
                            odoo_note_completed, customer_response_completed,
                            stage_update_completed, email_delivery_completed, processing_lease_until,
                            lease_owner_token, ambiguous_write_outcome, ambiguous_write_context
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ticket_id) DO UPDATE SET
                            fingerprint = excluded.fingerprint,
                            status = excluded.status,
                            last_decision = excluded.last_decision,
                            last_reason = excluded.last_reason,
                            updated_at = excluded.updated_at,
                            last_checked_at = excluded.last_checked_at,
                            retry_count = excluded.retry_count,
                            next_retry_at = excluded.next_retry_at,
                            last_error = excluded.last_error,
                            reactivation_completed = excluded.reactivation_completed,
                            reactivation_authorized = excluded.reactivation_authorized,
                            odoo_note_completed = excluded.odoo_note_completed,
                            customer_response_completed = excluded.customer_response_completed,
                            stage_update_completed = excluded.stage_update_completed,
                            email_delivery_completed = excluded.email_delivery_completed,
                            processing_lease_until = COALESCE(excluded.processing_lease_until, processing_lease_until),
                            lease_owner_token = COALESCE(excluded.lease_owner_token, lease_owner_token),
                            ambiguous_write_outcome = excluded.ambiguous_write_outcome,
                            ambiguous_write_context = excluded.ambiguous_write_context
                    """, (
                        state.ticket_id,
                        state.fingerprint,
                        state.status.value,
                        state.last_decision,
                        state.last_reason,
                        state.created_at.isoformat(),
                        state.updated_at.isoformat(),
                        state.last_checked_at.isoformat() if state.last_checked_at else None,
                        state.retry_count,
                        state.next_retry_at.isoformat() if state.next_retry_at else None,
                        state.last_error,
                        1 if state.reactivation_completed else 0,
                        1 if state.reactivation_authorized else 0,
                        1 if state.odoo_note_completed else 0,
                        1 if state.customer_response_completed else 0,
                        1 if state.stage_update_completed else 0,
                        1 if state.email_delivery_completed else 0,
                        state.processing_lease_until.isoformat() if state.processing_lease_until else None,
                        state.lease_owner_token,
                        state.ambiguous_write_outcome,
                        state.ambiguous_write_context,
                    ))

                conn.commit()
                logger.debug(f"Saved state for ticket {state.ticket_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to save state for ticket {state.ticket_id}: {str(e)}")
            return False

    def claim_for_processing(
        self, ticket_id: int, fingerprint: str, lease_duration_seconds: int = 300
    ) -> str:
        """Atomically claim a ticket for processing and return ownership token.

        ISSUE #2 FINAL FIX 1: Atomic claim using SQLite BEGIN IMMEDIATE.

        Ensures exactly one worker succeeds even with simultaneous claims on expired leases.
        Uses single conditional UPDATE to prevent race conditions.

        Only succeeds if:
        1. No state exists yet, OR
        2. Fingerprint matches (content unchanged), OR
        3. Previous PROCESSING lease has expired

        Args:
            ticket_id: Ticket ID to claim
            fingerprint: Current ticket fingerprint
            lease_duration_seconds: How long to hold the processing lease

        Returns:
            Ownership token if successful, None if another process holds it
        """
        try:
            now = datetime.now(timezone.utc)
            lease_until = now + timedelta(seconds=lease_duration_seconds)

            with sqlite3.connect(self.db_path) as conn:
                # FIX 1: Use BEGIN IMMEDIATE for atomic claim
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()

                try:
                    # Check current state
                    cursor.execute(
                        "SELECT status, fingerprint, processing_lease_until, lease_owner_token FROM automation_state WHERE ticket_id = ?",
                        (ticket_id,)
                    )
                    row = cursor.fetchone()

                    # Case 1: No state exists - create new processing state
                    if not row:
                        owner_token = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO automation_state (
                                ticket_id, fingerprint, status, created_at, updated_at,
                                retry_count, processing_lease_until, lease_owner_token
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            ticket_id,
                            fingerprint,
                            AutomationStatus.PROCESSING.value,
                            now.isoformat(),
                            now.isoformat(),
                            0,
                            lease_until.isoformat(),
                            owner_token,
                        ))
                        conn.commit()
                        logger.info(f"Claimed new ticket {ticket_id} for processing with token {owner_token[:8]}...")
                        return owner_token

                    status, stored_fingerprint, processing_lease_until_str, old_token = row

                    # Case 2: Active lease exists - reject claim (atomicity protected by BEGIN IMMEDIATE)
                    if processing_lease_until_str:
                        lease_until_dt = datetime.fromisoformat(processing_lease_until_str)
                        if now < lease_until_dt:
                            conn.rollback()
                            logger.warning(
                                f"Ticket {ticket_id} is already being processed (lease until {lease_until_dt})"
                            )
                            return None

                    # Case 3: Lease expired - reclaim atomically
                    # FIX 1: Use atomic UPDATE with WHERE condition to prevent second worker from succeeding
                    owner_token = str(uuid.uuid4())

                    # Atomic UPDATE: only succeed if lease is actually expired NOW
                    cursor.execute("""
                        UPDATE automation_state
                        SET status = ?, fingerprint = ?, processing_lease_until = ?, lease_owner_token = ?, updated_at = ?
                        WHERE ticket_id = ? AND (
                            processing_lease_until IS NULL OR
                            processing_lease_until <= ?
                        )
                    """, (
                        AutomationStatus.PROCESSING.value,
                        fingerprint,
                        lease_until.isoformat(),
                        owner_token,
                        now.isoformat(),
                        ticket_id,
                        now.isoformat()
                    ))

                    # FIX 1: Check rowcount - only one worker will succeed
                    if cursor.rowcount == 0:
                        conn.rollback()
                        logger.warning(
                            f"Ticket {ticket_id} reclaim failed - another worker claimed it first"
                        )
                        return None

                    conn.commit()
                    logger.info(f"Claimed ticket {ticket_id} for processing after expiration with token {owner_token[:8]}...")
                    return owner_token

                except Exception as inner_e:
                    conn.rollback()
                    raise inner_e

        except Exception as e:
            logger.error(f"Failed to claim ticket {ticket_id} for processing: {str(e)}")
            # ISSUE 4 FIX: Re-raise real database errors instead of returning None.
            # Only return None for legitimate contention (active lease or lost race).
            # All other exceptions indicate actual persistence failures.
            raise

    def mark_completed(self, ticket_id: int, owner_token: Optional[str] = None) -> bool:
        """Mark ticket processing as completed.

        ISSUE #2 FIX: Validates owner_token atomically in SQL to prevent stale workers
        from marking completion on active leases. Uses conditional UPDATE with rowcount check.

        Args:
            ticket_id: Ticket ID
            owner_token: Ownership token from claim_for_processing() - required for PROCESSING records

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # ISSUE #2 FIX: Atomic SQL validation - only update if token matches AND lease is active
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, updated_at = ?, processing_lease_until = NULL, lease_owner_token = NULL
                    WHERE ticket_id = ? AND (
                        lease_owner_token IS NULL OR
                        (lease_owner_token = ? AND (processing_lease_until IS NULL OR processing_lease_until > ?))
                    )
                """, (
                    AutomationStatus.COMPLETED.value,
                    now.isoformat(),
                    ticket_id,
                    owner_token,
                    now.isoformat()
                ))

                # Check if update succeeded (rowcount > 0 means validation passed)
                if cursor.rowcount == 0:
                    logger.warning(
                        f"Token validation failed for ticket {ticket_id}: "
                        f"mark_completed rejected (token mismatch or expired lease)"
                    )
                    return False

                conn.commit()
                logger.info(f"Marked ticket {ticket_id} as completed")
                return True

        except Exception as e:
            logger.error(f"Failed to mark ticket {ticket_id} as completed: {str(e)}")
            return False

    def mark_manual_review(self, ticket_id: int, reason: str, owner_token: Optional[str] = None) -> bool:
        """Mark ticket for manual review.

        ISSUE #2 FIX: Validates owner_token atomically in SQL to prevent stale workers
        from transitioning active leases. Uses conditional UPDATE with rowcount check.

        Args:
            ticket_id: Ticket ID
            reason: Reason for manual review
            owner_token: Ownership token from claim_for_processing() - required for PROCESSING records

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # ISSUE #2 FIX: Atomic SQL validation - only update if token matches AND lease is active
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, last_reason = ?, updated_at = ?, processing_lease_until = NULL, lease_owner_token = NULL
                    WHERE ticket_id = ? AND (
                        lease_owner_token IS NULL OR
                        (lease_owner_token = ? AND (processing_lease_until IS NULL OR processing_lease_until > ?))
                    )
                """, (
                    AutomationStatus.MANUAL_REVIEW.value,
                    reason,
                    now.isoformat(),
                    ticket_id,
                    owner_token,
                    now.isoformat()
                ))

                # Check if update succeeded (rowcount > 0 means validation passed)
                if cursor.rowcount == 0:
                    logger.warning(
                        f"Token validation failed for ticket {ticket_id}: "
                        f"mark_manual_review rejected (token mismatch or expired lease)"
                    )
                    return False

                conn.commit()
                logger.info(f"Marked ticket {ticket_id} for manual review")
                return True

        except Exception as e:
            logger.error(f"Failed to mark ticket {ticket_id} for manual review: {str(e)}")
            return False

    def mark_skipped(self, ticket_id: int, owner_token: Optional[str] = None) -> bool:
        """Mark ticket as skipped and release the processing lease.

        ISSUE #2 FIX: Terminal outcome that releases ownership.

        Args:
            ticket_id: Ticket ID
            owner_token: Ownership token from claim_for_processing() - required for PROCESSING records

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Atomic SQL validation - only update if token matches AND lease is active
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, updated_at = ?, processing_lease_until = NULL, lease_owner_token = NULL
                    WHERE ticket_id = ? AND (
                        lease_owner_token IS NULL OR
                        (lease_owner_token = ? AND (processing_lease_until IS NULL OR processing_lease_until > ?))
                    )
                """, (
                    AutomationStatus.SKIPPED.value,
                    now.isoformat(),
                    ticket_id,
                    owner_token,
                    now.isoformat()
                ))

                # Check if update succeeded (rowcount > 0 means validation passed)
                if cursor.rowcount == 0:
                    logger.warning(
                        f"Token validation failed for ticket {ticket_id}: "
                        f"mark_skipped rejected (token mismatch or expired lease)"
                    )
                    return False

                conn.commit()
                logger.info(f"Marked ticket {ticket_id} as skipped and released lease")
                return True

        except Exception as e:
            logger.error(f"Failed to mark ticket {ticket_id} as skipped: {str(e)}")
            return False

    def get_due_retries(self, limit: int = 50) -> list:
        """Get tickets scheduled for retry whose retry time has passed.

        TASK 1 FIX: Query automation_state database directly for due retries.
        This discovers retries regardless of Odoo ticket stage.

        Args:
            limit: Maximum number of retry tickets to return

        Returns:
            List of AutomationState objects with status=RETRY_SCHEDULED and next_retry_at <= now
        """
        try:
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # TASK 1 FIX: Query automation_state directly, not Odoo
                cursor.execute("""
                    SELECT * FROM automation_state
                    WHERE status = ? AND next_retry_at IS NOT NULL AND next_retry_at <= ?
                    ORDER BY next_retry_at ASC
                    LIMIT ?
                """, (AutomationStatus.RETRY_SCHEDULED.value, now.isoformat(), limit))

                rows = cursor.fetchall()
                return [self._row_to_state(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get due retries: {str(e)}")
            return []

    def get_expired_processing_tickets(self, limit: int = 50) -> list:
        """Get PROCESSING tickets whose leases have expired.

        TASK 4 FIX: Discover tickets stuck in PROCESSING status due to worker crash/timeout.
        These are safe to reclaim after their lease expires.

        Args:
            limit: Maximum number of expired tickets to return

        Returns:
            List of AutomationState objects with status=PROCESSING and expired processing_lease_until
        """
        try:
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # TASK 4 FIX: Find PROCESSING tickets with expired leases
                cursor.execute("""
                    SELECT * FROM automation_state
                    WHERE status = ? AND processing_lease_until IS NOT NULL AND processing_lease_until <= ?
                    ORDER BY processing_lease_until ASC
                    LIMIT ?
                """, (AutomationStatus.PROCESSING.value, now.isoformat(), limit))

                rows = cursor.fetchall()
                return [self._row_to_state(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get expired processing tickets: {str(e)}")
            return []

    def schedule_retry(
        self, ticket_id: int, retry_after_seconds: int = 3600, error: Optional[str] = None,
        owner_token: Optional[str] = None
    ) -> bool:
        """Schedule a ticket for retry.

        ISSUE #2 FIX: Validates owner_token atomically in SQL to prevent stale workers
        from releasing another worker's lease. Uses conditional UPDATE with rowcount check.

        Args:
            ticket_id: Ticket ID
            retry_after_seconds: How long to wait before retrying (default 1 hour)
            error: Error message to store
            owner_token: Ownership token from claim_for_processing() - required for PROCESSING records

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)
            next_retry = now + timedelta(seconds=retry_after_seconds)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # ISSUE #2 FIX: Atomic SQL validation - only update if token matches AND lease is active
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, retry_count = retry_count + 1,
                        next_retry_at = ?, last_error = ?, updated_at = ?,
                        processing_lease_until = NULL, lease_owner_token = NULL
                    WHERE ticket_id = ? AND (
                        lease_owner_token IS NULL OR
                        (lease_owner_token = ? AND (processing_lease_until IS NULL OR processing_lease_until > ?))
                    )
                """, (
                    AutomationStatus.RETRY_SCHEDULED.value,
                    next_retry.isoformat(),
                    error,
                    now.isoformat(),
                    ticket_id,
                    owner_token,
                    now.isoformat()
                ))

                # Check if update succeeded (rowcount > 0 means validation passed)
                if cursor.rowcount == 0:
                    logger.warning(
                        f"Token validation failed for ticket {ticket_id}: "
                        f"schedule_retry rejected (token mismatch or expired lease)"
                    )
                    return False

                conn.commit()
                logger.info(
                    f"Scheduled ticket {ticket_id} for retry at {next_retry} "
                    f"(attempt {cursor.rowcount})"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to schedule retry for ticket {ticket_id}: {str(e)}")
            return False

    def mark_communication_sent(
        self, ticket_id: int, event: "CommunicationEvent"
    ) -> bool:
        """Mark a communication event as sent for a ticket.

        Args:
            ticket_id: Ticket ID
            event: CommunicationEvent that was sent

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO communication_events
                    (ticket_id, event, sent_at)
                    VALUES (?, ?, ?)
                """, (ticket_id, event.value, now.isoformat()))

                conn.commit()
                logger.debug(f"Marked communication event {event.value} as sent for ticket {ticket_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to mark communication sent for ticket {ticket_id}: {str(e)}")
            return False

    def has_communication_sent(self, ticket_id: int, event: CommunicationEvent) -> bool:
        """Check if a communication event has been sent for a ticket.

        Args:
            ticket_id: Ticket ID
            event: CommunicationEvent to check

        Returns:
            True if event was sent, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM communication_events WHERE ticket_id = ? AND event = ?",
                    (ticket_id, event.value)
                )
                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check communication sent for ticket {ticket_id}: {str(e)}")
            return False

    def get_sent_communications(self, ticket_id: int) -> list:
        """Get all sent communication events for a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            List of CommunicationEvent values that were sent
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT event FROM communication_events WHERE ticket_id = ?",
                    (ticket_id,)
                )
                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get sent communications for ticket {ticket_id}: {str(e)}")
            return []

    def mark_communication_confirmed(
        self, ticket_id: int, confirmed_at: datetime
    ) -> bool:
        """Mark a ticket as confirmed by customer.

        Args:
            ticket_id: Ticket ID
            confirmed_at: When customer confirmed

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO customer_confirmations
                    (ticket_id, confirmed_at)
                    VALUES (?, ?)
                """, (ticket_id, confirmed_at.isoformat()))

                conn.commit()
                logger.debug(f"Marked ticket {ticket_id} as confirmed by customer")
                return True

        except Exception as e:
            logger.error(f"Failed to mark communication confirmed for ticket {ticket_id}: {str(e)}")
            return False

    def get_confirmation(self, ticket_id: int) -> Optional[datetime]:
        """Get customer confirmation timestamp for a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            Confirmation datetime if confirmed, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT confirmed_at FROM customer_confirmations WHERE ticket_id = ?",
                    (ticket_id,)
                )
                row = cursor.fetchone()
                if row:
                    return datetime.fromisoformat(row[0])
                return None

        except Exception as e:
            logger.error(f"Failed to get confirmation for ticket {ticket_id}: {str(e)}")
            return None

    def _row_to_state(self, row: sqlite3.Row) -> AutomationState:
        """Convert database row to AutomationState."""
        # P1-03: Handle email_delivery_completed field (backward compatibility)
        try:
            email_delivery_completed = bool(row["email_delivery_completed"])
        except (IndexError, KeyError):
            email_delivery_completed = False

        # TASK 3 FIX: Handle lease_owner_token field
        try:
            lease_owner_token = row["lease_owner_token"]
        except (IndexError, KeyError):
            lease_owner_token = None

        # P2 Issue #5: Handle ambiguous write outcome fields (backward compatibility)
        try:
            ambiguous_write_outcome = row["ambiguous_write_outcome"]
        except (IndexError, KeyError):
            ambiguous_write_outcome = None

        try:
            ambiguous_write_context = row["ambiguous_write_context"]
        except (IndexError, KeyError):
            ambiguous_write_context = None

        return AutomationState(
            ticket_id=row["ticket_id"],
            fingerprint=row["fingerprint"],
            status=AutomationStatus(row["status"]),
            last_decision=row["last_decision"],
            last_reason=row["last_reason"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_checked_at=datetime.fromisoformat(row["last_checked_at"]) if row["last_checked_at"] else None,
            retry_count=row["retry_count"],
            next_retry_at=datetime.fromisoformat(row["next_retry_at"]) if row["next_retry_at"] else None,
            last_error=row["last_error"],
            processing_lease_until=datetime.fromisoformat(row["processing_lease_until"]) if row["processing_lease_until"] else None,
            reactivation_completed=bool(row["reactivation_completed"]),
            reactivation_authorized=bool(row["reactivation_authorized"]),
            odoo_note_completed=bool(row["odoo_note_completed"]),
            customer_response_completed=bool(row["customer_response_completed"]),
            stage_update_completed=bool(row["stage_update_completed"]),
            email_delivery_completed=email_delivery_completed,
            lease_owner_token=lease_owner_token,
            ambiguous_write_outcome=ambiguous_write_outcome,
            ambiguous_write_context=ambiguous_write_context,
        )
