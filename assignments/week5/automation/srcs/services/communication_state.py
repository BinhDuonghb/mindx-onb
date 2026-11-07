"""Communication state tracking to prevent duplicate emails on re-polls."""

from dataclasses import dataclass, field
from typing import Set, Dict, Optional
from datetime import datetime, timezone
from srcs.services.gmail import CommunicationEvent


@dataclass
class TicketCommunicationState:
    """Track communication events sent for a ticket."""

    ticket_id: int
    events_sent: Set[CommunicationEvent] = field(default_factory=set)
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None

    def has_sent(self, event: CommunicationEvent) -> bool:
        """Check if an event has already been sent for this ticket."""
        return event in self.events_sent

    def mark_sent(self, event: CommunicationEvent) -> None:
        """Mark an event as sent for this ticket."""
        self.events_sent.add(event)
        self.last_updated_at = datetime.now(timezone.utc)

    def is_confirmed(self) -> bool:
        """Check if customer has confirmed resolution."""
        return self.confirmed_at is not None

    def mark_confirmed(self, confirmed_at: datetime) -> None:
        """Mark ticket as confirmed by customer."""
        self.confirmed_at = confirmed_at
        self.last_updated_at = datetime.now(timezone.utc)

    def reset(self) -> None:
        """Reset all sent events (useful for testing or manual reset)."""
        self.events_sent.clear()
        self.confirmed_at = None
        self.last_updated_at = datetime.now(timezone.utc)


class CommunicationStateTracker:
    """Track communication state to prevent duplicate emails.

    Maintains an in-memory registry of which communication events have been
    sent for each ticket, and tracks customer confirmation status.

    Prevents duplicate emails on repeated polling cycles and ensures tickets
    aren't closed until customer confirmation is received.
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

    def is_confirmed(self, ticket_id: int) -> bool:
        """Check if customer has confirmed resolution for a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            True if customer confirmed, False otherwise
        """
        if ticket_id not in self._state:
            return False

        return self._state[ticket_id].is_confirmed()

    def mark_confirmed(self, ticket_id: int, confirmed_at: datetime) -> None:
        """Record customer confirmation for a ticket.

        Args:
            ticket_id: Ticket ID
            confirmed_at: When customer confirmed the resolution
        """
        if ticket_id not in self._state:
            self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)

        self._state[ticket_id].mark_confirmed(confirmed_at)

    def get_confirmed_at(self, ticket_id: int) -> Optional[datetime]:
        """Get the confirmation timestamp for a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            Confirmation datetime if confirmed, None otherwise
        """
        if ticket_id not in self._state:
            return None

        return self._state[ticket_id].confirmed_at

    def get_state(self, ticket_id: int) -> TicketCommunicationState:
        """Get the communication state for a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            TicketCommunicationState with all sent events and confirmation
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
