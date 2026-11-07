"""AutomationStateRepository - SQLite persistence for automation processing state."""

from __future__ import annotations

import logging
import sqlite3
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
        """Initialize database schema."""
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
                        odoo_note_completed INTEGER NOT NULL DEFAULT 0,
                        customer_response_completed INTEGER NOT NULL DEFAULT 0,
                        stage_update_completed INTEGER NOT NULL DEFAULT 0,
                        processing_lease_until TEXT
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
                logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

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

    def save(self, state: AutomationState) -> bool:
        """Save or update automation state (upsert).

        Args:
            state: AutomationState to save

        Returns:
            True if successful, False otherwise
        """
        try:
            state.updated_at = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO automation_state (
                        ticket_id, fingerprint, status, last_decision, last_reason,
                        created_at, updated_at, last_checked_at, retry_count,
                        next_retry_at, last_error, reactivation_completed,
                        odoo_note_completed, customer_response_completed,
                        stage_update_completed, processing_lease_until
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        odoo_note_completed = excluded.odoo_note_completed,
                        customer_response_completed = excluded.customer_response_completed,
                        stage_update_completed = excluded.stage_update_completed,
                        processing_lease_until = excluded.processing_lease_until
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
                    1 if state.odoo_note_completed else 0,
                    1 if state.customer_response_completed else 0,
                    1 if state.stage_update_completed else 0,
                    None,
                ))

                conn.commit()
                logger.debug(f"Saved state for ticket {state.ticket_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to save state for ticket {state.ticket_id}: {str(e)}")
            return False

    def claim_for_processing(
        self, ticket_id: int, fingerprint: str, lease_duration_seconds: int = 300
    ) -> bool:
        """Atomically claim a ticket for processing.

        Prevents duplicate concurrent processing by setting a processing lease.
        Only succeeds if:
        1. No state exists yet, OR
        2. Fingerprint matches (content unchanged), OR
        3. Previous PROCESSING lease has expired

        Args:
            ticket_id: Ticket ID to claim
            fingerprint: Current ticket fingerprint
            lease_duration_seconds: How long to hold the processing lease

        Returns:
            True if claim successful, False if another process holds it
        """
        try:
            now = datetime.now(timezone.utc)
            lease_until = now + timedelta(seconds=lease_duration_seconds)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check current state
                cursor.execute(
                    "SELECT status, fingerprint, processing_lease_until FROM automation_state WHERE ticket_id = ?",
                    (ticket_id,)
                )
                row = cursor.fetchone()

                # No state exists - create new processing state with lease
                if not row:
                    cursor.execute("""
                        INSERT INTO automation_state (
                            ticket_id, fingerprint, status, created_at, updated_at,
                            retry_count, processing_lease_until
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ticket_id,
                        fingerprint,
                        AutomationStatus.PROCESSING.value,
                        now.isoformat(),
                        now.isoformat(),
                        0,
                        lease_until.isoformat(),
                    ))
                    conn.commit()
                    logger.info(f"Claimed new ticket {ticket_id} for processing")
                    return True

                status, stored_fingerprint, processing_lease_until_str = row

                # Check if processing lease has expired (BEFORE checking fingerprint)
                # Active leases cannot be bypassed by fingerprint changes
                if processing_lease_until_str:
                    lease_until_dt = datetime.fromisoformat(processing_lease_until_str)
                    if now < lease_until_dt:
                        logger.warning(
                            f"Ticket {ticket_id} is already being processed (lease until {lease_until_dt})"
                        )
                        return False
                    else:
                        logger.warning(
                            f"Recovering stale processing for ticket {ticket_id} (lease expired at {lease_until_dt})"
                        )

                # Fingerprint changed - allow re-evaluation (only if no active lease)
                if stored_fingerprint != fingerprint:
                    logger.info(
                        f"Ticket {ticket_id} fingerprint changed - allowing re-evaluation"
                    )
                    # Update fingerprint and status to PENDING for re-evaluation
                    cursor.execute("""
                        UPDATE automation_state
                        SET fingerprint = ?, status = ?, processing_lease_until = NULL
                        WHERE ticket_id = ?
                    """, (fingerprint, AutomationStatus.PENDING.value, ticket_id))
                    conn.commit()
                    return True

                # Claim for processing
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, processing_lease_until = ?
                    WHERE ticket_id = ?
                """, (AutomationStatus.PROCESSING.value, lease_until.isoformat(), ticket_id))

                conn.commit()
                logger.info(f"Claimed ticket {ticket_id} for processing")
                return True

        except Exception as e:
            logger.error(f"Failed to claim ticket {ticket_id} for processing: {str(e)}")
            return False

    def mark_completed(self, ticket_id: int) -> bool:
        """Mark ticket processing as completed.

        Args:
            ticket_id: Ticket ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, updated_at = ?, processing_lease_until = NULL
                    WHERE ticket_id = ?
                """, (
                    AutomationStatus.COMPLETED.value,
                    datetime.now(timezone.utc).isoformat(),
                    ticket_id
                ))
                conn.commit()
                logger.info(f"Marked ticket {ticket_id} as completed")
                return True

        except Exception as e:
            logger.error(f"Failed to mark ticket {ticket_id} as completed: {str(e)}")
            return False

    def mark_manual_review(self, ticket_id: int, reason: str) -> bool:
        """Mark ticket for manual review.

        Args:
            ticket_id: Ticket ID
            reason: Reason for manual review

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, last_reason = ?, updated_at = ?, processing_lease_until = NULL
                    WHERE ticket_id = ?
                """, (
                    AutomationStatus.MANUAL_REVIEW.value,
                    reason,
                    datetime.now(timezone.utc).isoformat(),
                    ticket_id
                ))
                conn.commit()
                logger.info(f"Marked ticket {ticket_id} for manual review")
                return True

        except Exception as e:
            logger.error(f"Failed to mark ticket {ticket_id} for manual review: {str(e)}")
            return False

    def schedule_retry(
        self, ticket_id: int, retry_after_seconds: int = 3600, error: Optional[str] = None
    ) -> bool:
        """Schedule a ticket for retry.

        Args:
            ticket_id: Ticket ID
            retry_after_seconds: How long to wait before retrying (default 1 hour)
            error: Error message to store

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)
            next_retry = now + timedelta(seconds=retry_after_seconds)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE automation_state
                    SET status = ?, retry_count = retry_count + 1,
                        next_retry_at = ?, last_error = ?, updated_at = ?,
                        processing_lease_until = NULL
                    WHERE ticket_id = ?
                """, (
                    AutomationStatus.RETRY_SCHEDULED.value,
                    next_retry.isoformat(),
                    error,
                    now.isoformat(),
                    ticket_id
                ))
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
            odoo_note_completed=bool(row["odoo_note_completed"]),
            customer_response_completed=bool(row["customer_response_completed"]),
            stage_update_completed=bool(row["stage_update_completed"]),
        )
