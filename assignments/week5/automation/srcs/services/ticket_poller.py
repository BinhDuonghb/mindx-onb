"""TicketPoller - Batch ticket fetching and processing."""

import logging
from typing import Optional, List, Tuple, TYPE_CHECKING, Any
from datetime import datetime, timedelta, UTC

from srcs.models import Ticket, AutomationState, AutomationStatus
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.repositories.automation_state_repository import AutomationStateRepository

if TYPE_CHECKING:
    from srcs.clients import TicketClient

logger = logging.getLogger(__name__)


class TicketPoller:
    """Polls Odoo for new/updated tickets and processes them.

    Handles:
    - Fetching unprocessed tickets from Odoo
    - Detecting new vs. updated tickets via fingerprinting
    - Queueing for automation processing
    - Tracking processing state in persistent repository

    Example:
        poller = TicketPoller(ticket_client, state_repo)

        # One-time poll: fetch and prepare tickets
        tickets = poller.poll(limit=10)

        # Process each ticket's automation
        for ticket in tickets:
            state = state_repo.get(ticket.id)
            # ... run automation logic ...
            state_repo.save(state)
    """

    def __init__(
        self,
        ticket_client: Any,
        state_repo: AutomationStateRepository,
    ):
        """Initialize poller.

        Args:
            ticket_client: Odoo ticket API client
            state_repo: AutomationState persistence repository
        """
        self.ticket_client = ticket_client
        self.state_repo = state_repo

    def poll(
        self,
        limit: int = 50,
        min_age_minutes: int = 0,
    ) -> List[Ticket]:
        """Poll Odoo for unprocessed tickets.

        Fetches tickets with status "new" or "pending" that haven't been
        processed yet, or have been updated since last processing.

        Args:
            limit: Maximum tickets to fetch per poll
            min_age_minutes: Only fetch tickets older than this (prevents
                            processing very new tickets that may still be edited)

        Returns:
            List of tickets ready for automation processing
        """
        try:
            # Fetch unprocessed ticket IDs from Odoo
            ticket_ids = self.ticket_client.search_tickets(
                domain=[("stage_id", "in", [1, 2])],  # new, pending stages
                limit=limit,
            )

            if not ticket_ids:
                logger.debug("No unprocessed tickets found")
                return []

            logger.info(f"Polled {len(ticket_ids)} unprocessed ticket IDs from Odoo")

            # Fetch full ticket data for each ID
            tickets = []
            for ticket_id in ticket_ids:
                try:
                    ticket = self.ticket_client.get_ticket(ticket_id)
                    if ticket:
                        tickets.append(ticket)
                except Exception as e:
                    logger.warning(f"Failed to fetch ticket {ticket_id}: {str(e)}")
                    continue

            if not tickets:
                logger.info("No valid tickets retrieved")
                return []

            logger.info(f"Retrieved {len(tickets)} tickets from Odoo")

            # Filter by age and fingerprint
            ready_tickets = []
            for ticket in tickets:
                if self._is_ready_for_processing(ticket, min_age_minutes):
                    ready_tickets.append(ticket)

            logger.info(f"Queued {len(ready_tickets)} tickets for processing")
            return ready_tickets

        except Exception as e:
            logger.error(f"Failed to poll tickets: {str(e)}")
            return []

    def poll_for_retry(self, limit: int = 50) -> List[Tuple[Ticket, AutomationState]]:
        """Poll for tickets scheduled for retry.

        Returns tickets that were previously processed but scheduled for retry
        (e.g., transient failures that need re-attempt).

        Args:
            limit: Maximum tickets to fetch

        Returns:
            List of (Ticket, AutomationState) tuples ready for retry
        """
        try:
            # Get tickets with RETRY_SCHEDULED status and retry time passed
            retry_tickets = []

            # Fetch all ticket IDs (this is a limitation of current design)
            # In production, might store retry queue separately
            ticket_ids = self.ticket_client.search_tickets(
                domain=[("stage_id", "in", [1, 2])],
                limit=limit * 5,  # Over-fetch since most won't be retry scheduled
            )

            for ticket_id in ticket_ids:
                try:
                    ticket = self.ticket_client.get_ticket(ticket_id)
                    if not ticket:
                        continue

                    state = self.state_repo.get(ticket.id)
                    if state and state.is_ready_for_retry():
                        retry_tickets.append((ticket, state))

                    if len(retry_tickets) >= limit:
                        break
                except Exception as e:
                    logger.warning(f"Failed to fetch ticket {ticket_id} for retry check: {str(e)}")
                    continue

            logger.info(f"Found {len(retry_tickets)} tickets ready for retry")
            return retry_tickets

        except Exception as e:
            logger.error(f"Failed to poll for retries: {str(e)}")
            return []

    def _is_ready_for_processing(
        self, ticket: Ticket, min_age_minutes: int = 0
    ) -> bool:
        """Check if ticket is ready for automation processing.

        Ticket is ready if:
        1. Never processed before, OR
        2. Content has changed (fingerprint mismatch)

        Args:
            ticket: Ticket to check
            min_age_minutes: Minimum age before processing

        Returns:
            True if ready for processing
        """
        # Check minimum age
        if min_age_minutes > 0 and ticket.create_date:
            # Handle both naive and aware datetimes
            create_dt = ticket.create_date
            now = datetime.now(UTC)

            # If create_date is naive, assume it's UTC and make it aware
            if create_dt.tzinfo is None:
                create_dt = create_dt.replace(tzinfo=UTC)

            age = now - create_dt
            if age < timedelta(minutes=min_age_minutes):
                logger.debug(
                    f"Ticket {ticket.id} too new ({age.total_seconds():.0f}s old), skipping"
                )
                return False

        # Get stored state
        state = self.state_repo.get(ticket.id)

        # New ticket - never processed
        if not state:
            logger.debug(f"Ticket {ticket.id} not processed before - queuing")
            return True

        # Already processing - don't queue again yet
        if state.status == AutomationStatus.PROCESSING:
            logger.debug(f"Ticket {ticket.id} already processing")
            return False

        # Content changed - allow re-evaluation
        current_fp = TicketFingerprinter.generate(ticket)
        if TicketFingerprinter.has_changed(ticket, state.fingerprint):
            logger.info(
                f"Ticket {ticket.id} content changed - re-queuing for evaluation"
            )
            return True

        # Already processed and unchanged
        logger.debug(f"Ticket {ticket.id} already processed with same content")
        return False


class PollingMetrics:
    """Tracks polling performance metrics."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.total_polls = 0
        self.total_tickets_fetched = 0
        self.total_tickets_queued = 0
        self.total_retries_found = 0
        self.last_poll_time: Optional[datetime] = None
        self.last_poll_count = 0

    def record_poll(self, fetched: int, queued: int) -> None:
        """Record a polling operation.

        Args:
            fetched: Number of tickets fetched from Odoo
            queued: Number of tickets queued for processing
        """
        self.total_polls += 1
        self.total_tickets_fetched += fetched
        self.total_tickets_queued += queued
        self.last_poll_time = datetime.now(UTC)
        self.last_poll_count = queued

    def record_retry_poll(self, retries: int) -> None:
        """Record a retry polling operation.

        Args:
            retries: Number of tickets found for retry
        """
        self.total_retries_found += retries

    def to_dict(self) -> dict:
        """Convert metrics to dictionary.

        Returns:
            Metrics summary
        """
        return {
            "total_polls": self.total_polls,
            "total_tickets_fetched": self.total_tickets_fetched,
            "total_tickets_queued": self.total_tickets_queued,
            "total_retries_found": self.total_retries_found,
            "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None,
            "last_poll_count": self.last_poll_count,
        }
