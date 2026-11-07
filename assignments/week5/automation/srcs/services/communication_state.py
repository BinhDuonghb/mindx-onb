"""Communication state tracking to prevent duplicate emails on re-polls."""

import logging
from dataclasses import dataclass, field
from typing import Set, Dict, Optional
from datetime import datetime, timezone
from srcs.services.gmail import CommunicationEvent

logger = logging.getLogger(__name__)


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

    Maintains a registry (in-memory or persistent) of which communication events
    have been sent for each ticket, and tracks customer confirmation status.

    Prevents duplicate emails on repeated polling cycles and ensures tickets
    aren't closed until customer confirmation is received.

    Optional SQLite persistence via AutomationStateRepository prevents duplicate
    emails even after process restart.
    """

    def __init__(self, repo=None):
        """Initialize tracker with optional persistence.

        Args:
            repo: Optional AutomationStateRepository for persistent communication state.
                  If None, uses in-memory tracking only (backwards compatible).
        """
        self._state: Dict[int, TicketCommunicationState] = {}
        self._repo = repo

        # Load persisted state from repo if available
        if self._repo:
            self._load_persisted_state()

    def _load_persisted_state(self) -> None:
        """Load persisted communication state from repository."""
        if not self._repo:
            return

        # Note: This is a best-effort load. In a real scenario, we'd need to
        # track which tickets have persisted state, but for now we load on-demand.
        logger.debug("Persistent communication state repository configured")

    def should_send(self, ticket_id: int, event: CommunicationEvent) -> bool:
        """Check if an email should be sent for this ticket+event combination.

        Checks both in-memory state and persisted repository.

        Args:
            ticket_id: Ticket ID
            event: Communication event

        Returns:
            True if email should be sent (not previously sent), False otherwise
        """
        # Check in-memory state first
        if ticket_id in self._state:
            state = self._state[ticket_id]
            if state.has_sent(event):
                return False

        # Check persisted repository
        if self._repo:
            if self._repo.has_communication_sent(ticket_id, event):
                # Load into memory for future checks
                if ticket_id not in self._state:
                    self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)
                self._state[ticket_id].mark_sent(event)
                return False

        return True

    def mark_sent(self, ticket_id: int, event: CommunicationEvent) -> None:
        """Mark an event as sent for a ticket.

        Persists to repository if available.

        Args:
            ticket_id: Ticket ID
            event: Communication event that was sent
        """
        if ticket_id not in self._state:
            self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)

        self._state[ticket_id].mark_sent(event)

        # Persist to repository if available
        if self._repo:
            self._repo.mark_communication_sent(ticket_id, event)

    def is_confirmed(self, ticket_id: int) -> bool:
        """Check if customer has confirmed resolution for a ticket.

        Checks both in-memory state and persisted repository.

        Args:
            ticket_id: Ticket ID

        Returns:
            True if customer confirmed, False otherwise
        """
        # Check in-memory state first
        if ticket_id in self._state and self._state[ticket_id].is_confirmed():
            return True

        # Check persisted repository
        if self._repo:
            confirmed_at = self._repo.get_confirmation(ticket_id)
            if confirmed_at:
                # Load into memory for future checks
                if ticket_id not in self._state:
                    self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)
                self._state[ticket_id].mark_confirmed(confirmed_at)
                return True

        return False

    def mark_confirmed(self, ticket_id: int, confirmed_at: datetime) -> None:
        """Record customer confirmation for a ticket.

        Persists to repository if available.

        Args:
            ticket_id: Ticket ID
            confirmed_at: When customer confirmed the resolution
        """
        if ticket_id not in self._state:
            self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)

        self._state[ticket_id].mark_confirmed(confirmed_at)

        # Persist to repository if available
        if self._repo:
            self._repo.mark_communication_confirmed(ticket_id, confirmed_at)

    def get_confirmed_at(self, ticket_id: int) -> Optional[datetime]:
        """Get the confirmation timestamp for a ticket.

        Checks both in-memory state and persisted repository.

        Args:
            ticket_id: Ticket ID

        Returns:
            Confirmation datetime if confirmed, None otherwise
        """
        # Check in-memory state first
        if ticket_id in self._state and self._state[ticket_id].confirmed_at:
            return self._state[ticket_id].confirmed_at

        # Check persisted repository
        if self._repo:
            confirmed_at = self._repo.get_confirmation(ticket_id)
            if confirmed_at:
                # Load into memory for future checks
                if ticket_id not in self._state:
                    self._state[ticket_id] = TicketCommunicationState(ticket_id=ticket_id)
                self._state[ticket_id].mark_confirmed(confirmed_at)
                return confirmed_at

        return None

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
