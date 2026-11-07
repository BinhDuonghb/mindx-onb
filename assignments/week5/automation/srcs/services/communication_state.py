"""Communication state tracking to prevent duplicate emails on re-polls."""

from dataclasses import dataclass, field
from typing import Set, Dict
from datetime import datetime, timezone
from srcs.services.gmail import CommunicationEvent


@dataclass
class TicketCommunicationState:
    """Track communication events sent for a ticket."""

    ticket_id: int
    events_sent: Set[CommunicationEvent] = field(default_factory=set)
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def has_sent(self, event: CommunicationEvent) -> bool:
        """Check if an event has already been sent for this ticket."""
        return event in self.events_sent

    def mark_sent(self, event: CommunicationEvent) -> None:
        """Mark an event as sent for this ticket."""
        self.events_sent.add(event)
        self.last_updated_at = datetime.now(timezone.utc)

    def reset(self) -> None:
        """Reset all sent events (useful for testing or manual reset)."""
        self.events_sent.clear()
        self.last_updated_at = datetime.now(timezone.utc)


class CommunicationStateTracker:
    """Track communication state to prevent duplicate emails.

    Maintains an in-memory registry of which communication events have been
    sent for each ticket. Prevents duplicate emails on repeated polling cycles.

    This is a simple in-memory tracker for Phase 5. Future phases can extend
    this with persistent storage (JSON, database, etc.).
    """

    def __init__(self):
        """Initialize tracker with empty state."""
        self._state: Dict[int, TicketCommunicationState] = {}

    def should_send(self, ticket_id: int, event: CommunicationEvent) -> bool:
        """Check if an email should be sent for this ticket+event combination.

        Args:
            ticket_id: Ticket ID
            event: Communication event

        Returns:
            True if email should be sent (not previously sent), False otherwise
        """
        if ticket_id not in self._state:
            return True

        state = self._state[ticket_id]
        return not state.has_sent(event)

    def mark_sent(self, ticket_id: int, event: CommunicationEvent) -> None:
        """Mark an event as sent for a ticket.

        Args:
            ticket_id: Ticket ID
            event: Communication event that was sent
        """
        if ticket_id not in self._state:
            self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)

        self._state[ticket_id].mark_sent(event)

    def get_state(self, ticket_id: int) -> TicketCommunicationState:
        """Get the communication state for a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            TicketCommunicationState with all sent events
        """
        if ticket_id not in self._state:
            self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)
        return self._state[ticket_id]

    def reset(self, ticket_id: int) -> None:
        """Reset communication state for a ticket (for testing or manual reset).

        Args:
            ticket_id: Ticket ID to reset
        """
        if ticket_id in self._state:
            self._state[ticket_id].reset()

    def reset_all(self) -> None:
        """Reset all communication state (for testing)."""
        self._state.clear()
