"""AutomationState model - Persistent processing state for each Odoo ticket."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AutomationStatus(str, Enum):
    """Processing status for automation workflow."""

    PENDING = "pending"  # Not yet processed
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"  # Successfully completed
    MANUAL_REVIEW = "manual_review"  # Escalated for manual review
    SKIPPED = "skipped"  # Not applicable (e.g., not a login issue)
    RETRY_SCHEDULED = "retry_scheduled"  # Failed, scheduled for retry
    FAILED = "failed"  # Permanently failed after retries


@dataclass
class AutomationState:
    """Represents persistent automation processing state for a ticket.

    Tracks whether a ticket has been processed, what decision was made,
    and whether any actions were taken. Distinguishes between business
    decision (e.g., APPROVE_REACTIVATION) and processing status (e.g.,
    COMPLETED or RETRY_SCHEDULED).

    Example:
        Decision: APPROVE_REACTIVATION, Status: COMPLETED
        → Account was successfully reactivated

        Decision: APPROVE_REACTIVATION, Status: RETRY_SCHEDULED
        → Reactivation approved but Odoo communication failed; retry scheduled

        Decision: SKIP, Status: COMPLETED
        → Ticket is not a login issue; automation skipped
    """

    ticket_id: int
    fingerprint: str  # SHA-256 hash of ticket content for change detection
    status: AutomationStatus
    last_decision: Optional[str] = None  # Business decision (e.g., "approve_reactivation")
    last_reason: Optional[str] = None  # Reason for the decision

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_checked_at: Optional[datetime] = None

    retry_count: int = 0
    next_retry_at: Optional[datetime] = None

    last_error: Optional[str] = None

    # Processing lease for preventing concurrent execution
    processing_lease_until: Optional[datetime] = None

    # TASK 3 FIX: Lease ownership token for preventing stale workers from overwriting state
    # Generated when claiming, validated on updates
    lease_owner_token: Optional[str] = None

    # Optional: Track which side effects have actually completed
    # These represent CONFIRMED actions, not attempted ones
    reactivation_completed: bool = False
    reactivation_authorized: bool = False  # Persisted proof of prior VERIFIED approval, not inferred from LMS status
    odoo_note_completed: bool = False
    customer_response_completed: bool = False
    stage_update_completed: bool = False
    email_delivery_completed: bool = False  # P1-03: Track email delivery success separately

    # P2 Issue #5: Track ambiguous Odoo write outcomes
    # Distinguishes between confirmed success/failure and unknown outcomes
    # Format: "operation_type:status" e.g., "message_post:unknown", "write:confirmed_failure"
    ambiguous_write_outcome: Optional[str] = None
    ambiguous_write_context: Optional[str] = None  # Error message or context for manual review

    def __post_init__(self) -> None:
        """Validate state after initialization."""
        if not self.ticket_id or self.ticket_id <= 0:
            raise ValueError("Ticket ID must be positive")
        if not self.fingerprint or not self.fingerprint.strip():
            raise ValueError("Fingerprint cannot be empty")

    def is_ready_for_retry(self) -> bool:
        """Check if ticket is ready for retry."""
        if self.status != AutomationStatus.RETRY_SCHEDULED:
            return False
        if self.next_retry_at is None:
            return True
        return datetime.now(timezone.utc) >= self.next_retry_at

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ticket_id": self.ticket_id,
            "fingerprint": self.fingerprint,
            "status": self.status.value,
            "last_decision": self.last_decision,
            "last_reason": self.last_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "last_error": self.last_error,
            "reactivation_completed": self.reactivation_completed,
            "reactivation_authorized": self.reactivation_authorized,
            "odoo_note_completed": self.odoo_note_completed,
            "customer_response_completed": self.customer_response_completed,
            "stage_update_completed": self.stage_update_completed,
            "email_delivery_completed": self.email_delivery_completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AutomationState":
        """Create from dictionary (deserialization)."""
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        updated_at = datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"]

        last_checked_at = None
        if data.get("last_checked_at"):
            last_checked_at = datetime.fromisoformat(data["last_checked_at"]) if isinstance(data["last_checked_at"], str) else data["last_checked_at"]

        next_retry_at = None
        if data.get("next_retry_at"):
            next_retry_at = datetime.fromisoformat(data["next_retry_at"]) if isinstance(data["next_retry_at"], str) else data["next_retry_at"]

        return cls(
            ticket_id=data["ticket_id"],
            fingerprint=data["fingerprint"],
            status=AutomationStatus(data["status"]),
            last_decision=data.get("last_decision"),
            last_reason=data.get("last_reason"),
            created_at=created_at,
            updated_at=updated_at,
            last_checked_at=last_checked_at,
            retry_count=data.get("retry_count", 0),
            next_retry_at=next_retry_at,
            last_error=data.get("last_error"),
            reactivation_completed=data.get("reactivation_completed", False),
            reactivation_authorized=data.get("reactivation_authorized", False),
            odoo_note_completed=data.get("odoo_note_completed", False),
            customer_response_completed=data.get("customer_response_completed", False),
            stage_update_completed=data.get("stage_update_completed", False),
            email_delivery_completed=data.get("email_delivery_completed", False),
        )
