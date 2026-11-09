"""Write operation outcomes for Odoo client.

P2 Issue #5: Distinguish between successful, confirmed failure, and unknown outcomes
for non-idempotent operations like message_post and write.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WriteOutcomeStatus(str, Enum):
    """Outcome status for a non-idempotent write operation."""

    SUCCESS = "success"  # Operation confirmed to have succeeded on server
    CONFIRMED_FAILURE = "confirmed_failure"  # Reliable evidence of non-execution
    UNKNOWN = "unknown"  # Server may have committed the operation; response was lost


@dataclass
class WriteOutcome:
    """Result of a non-idempotent write operation.

    Distinguishes between:
    - SUCCESS: Response received, server confirmed execution
    - CONFIRMED_FAILURE: Reliable evidence that server rejected or did not execute
    - UNKNOWN: Timeout/ambiguous response - server may have executed

    Backward compatible with boolean: bool(WriteOutcome(...)) returns True for SUCCESS.
    """

    status: WriteOutcomeStatus
    error: Optional[str] = None  # Error message if applicable
    server_message: Optional[str] = None  # Server response if available
    is_retryable: bool = False  # Only True for CONFIRMED_FAILURE with safe preconditions

    def is_success(self) -> bool:
        """Check if operation succeeded."""
        return self.status == WriteOutcomeStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if operation definitely failed (safe to retry)."""
        return self.status == WriteOutcomeStatus.CONFIRMED_FAILURE

    def is_unknown(self) -> bool:
        """Check if operation outcome is unknown (ambiguous)."""
        return self.status == WriteOutcomeStatus.UNKNOWN

    def __bool__(self) -> bool:
        """Backward compatibility: bool(outcome) returns True for SUCCESS.

        This allows existing code like:
            if outcome:  # Equivalent to: if outcome.is_success()
                ...
        """
        return self.is_success()

    def __str__(self) -> str:
        """Human-readable representation."""
        if self.error:
            return f"{self.status.value}: {self.error}"
        return self.status.value
