"""Automation workflow result model."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class ActionTaken(str, Enum):
    """Actions that can be taken by the automation."""
    ACCOUNT_REACTIVATED = "account_reactivated"
    ESCALATED_TERMINATED = "escalated_terminated"
    ESCALATED_ERROR = "escalated_error"
    NO_ACTION = "no_action"
    QUEUED_RETRY = "queued_retry"


class ResultStatus(str, Enum):
    """Overall result status."""
    SUCCESS = "success"
    ESCALATED = "escalated"
    QUEUED = "queued"
    FAILED = "failed"


@dataclass
class AutomationResult:
    """Result of an automation workflow execution.

    Captures the outcome of processing a single ticket through
    the full automation pipeline.
    """

    ticket_id: int
    status: ResultStatus
    action_taken: ActionTaken
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Error details (if applicable)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[dict] = None

    # Audit trail
    employee_id: Optional[int] = None
    employee_status: Optional[str] = None
    hr_query_successful: bool = True

    # Retry info
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate result data after initialization."""
        if not self.ticket_id or self.ticket_id <= 0:
            raise ValueError("Ticket ID must be positive")
        if not self.message or not self.message.strip():
            raise ValueError("Message cannot be empty")

    def is_success(self) -> bool:
        """Check if automation completed successfully."""
        return self.status == ResultStatus.SUCCESS

    def is_escalated(self) -> bool:
        """Check if ticket was escalated for manual review."""
        return self.status == ResultStatus.ESCALATED

    def is_queued(self) -> bool:
        """Check if automation is queued for retry."""
        return self.status == ResultStatus.QUEUED

    def is_error(self) -> bool:
        """Check if automation failed with error."""
        return self.status == ResultStatus.FAILED or self.error_type is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization and logging."""
        return {
            "ticket_id": self.ticket_id,
            "status": self.status.value,
            "action_taken": self.action_taken.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "employee_id": self.employee_id,
            "employee_status": self.employee_status,
            "hr_query_successful": self.hr_query_successful,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
        }

    def __str__(self) -> str:
        """Human-readable result summary."""
        base = f"Ticket #{self.ticket_id}: {self.status.value} - {self.action_taken.value}"
        if self.error_type:
            base += f" (Error: {self.error_type})"
        return base
