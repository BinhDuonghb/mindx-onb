"""Odoo Ticket System API Client using JSON-2 API."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from srcs.clients.odoo.base import ODOOClient
from srcs.models import Ticket

logger = logging.getLogger(__name__)


class TicketClient(ODOOClient):
    """Client for Odoo helpdesk.ticket integration via JSON-2 API.

    Handles read-only operations on tickets for the automation workflow:
    - Discover tickets matching patterns (e.g., recent login issues)
    - Fetch ticket details for analysis
    - Update ticket notes after automation actions

    JSON-2 API Format: POST /json/2/<model>/<method>
    Parameters go at TOP LEVEL of request, not nested in params.
    """

    MODEL_NAME = "helpdesk.ticket"

    def __init__(
        self,
        api_endpoint: str,
        database: str,
        headers: Dict[str, str],
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize Odoo ticket client.

        Args:
            api_endpoint: Odoo JSON-2 API endpoint (e.g., https://example.odoo.com/json/2)
            database: Odoo database name
            headers: HTTP headers including Bearer token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        super().__init__(api_endpoint, headers, timeout, max_retries)
        self.database = database

    def search_tickets(
        self,
        domain: Optional[List[Any]] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "create_date DESC",
    ) -> List[int]:
        """Search for tickets matching criteria.

        Args:
            domain: Search domain filter (Odoo format)
                   e.g., [("stage_id.name", "=", "New")]
            limit: Maximum number of results
            offset: Result offset for pagination
            order: Sort order

        Returns:
            List of ticket IDs matching the search
        """
        if domain is None:
            domain = []

        # JSON-2 API endpoint: POST /json/2/helpdesk.ticket/search
        endpoint = f"/{self.MODEL_NAME}/search"

        # Parameters go at TOP LEVEL of request
        payload = {
            "domain": domain,
            "limit": limit,
            "offset": offset,
            "order": order,
        }

        try:
            logger.debug(f"Searching tickets with domain: {domain}")
            response = self.post(endpoint, json=payload)
            result = response.json()

            logger.debug(f"Found {len(result)} tickets matching search criteria")
            return result

        except Exception as e:
            logger.error(f"Failed to search tickets: {str(e)}")
            return []

    def read_tickets(
        self,
        ticket_ids: List[int],
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Read ticket data from Odoo.

        Args:
            ticket_ids: List of ticket IDs to read
            fields: Specific fields to retrieve
                   If None, retrieves common fields

        Returns:
            List of ticket data dictionaries
        """
        if not ticket_ids:
            return []

        if fields is None:
            fields = [
                "id", "name", "partner_email", "description",
                "stage_id", "partner_id",
                "create_date", "write_date", "priority",
            ]

        # JSON-2 API endpoint: POST /json/2/helpdesk.ticket/read
        endpoint = f"/{self.MODEL_NAME}/read"

        # Parameters go at TOP LEVEL of request
        payload = {
            "ids": ticket_ids,
            "fields": fields,
        }

        try:
            logger.debug(f"Reading {len(ticket_ids)} tickets with fields: {fields}")
            response = self.post(endpoint, json=payload)
            result = response.json()

            logger.debug(f"Read {len(result)} ticket records")
            return result

        except Exception as e:
            logger.error(f"Failed to read tickets: {str(e)}")
            return []

    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Get a single ticket as a Ticket model.

        Args:
            ticket_id: Ticket ID to retrieve

        Returns:
            Ticket model or None if not found
        """
        try:
            tickets = self.read_tickets([ticket_id])
            if not tickets:
                logger.warning(f"Ticket {ticket_id} not found")
                return None

            ticket_data = tickets[0]
            return self._parse_ticket(ticket_data)

        except Exception as e:
            logger.error(f"Failed to get ticket {ticket_id}: {str(e)}")
            return None

    def add_log(self, ticket_id: int, log_message: str, is_internal: bool = True) -> bool:
        """Add a log/notification message to a ticket.

        Args:
            ticket_id: Ticket ID
            log_message: Log message text
            is_internal: If True, internal note (not sent to customer).
                        If False, visible comment (sent to customer).

        Returns:
            True if successful
        """
        # JSON-2 API endpoint: POST /json/2/helpdesk.ticket/message_post
        endpoint = f"/{self.MODEL_NAME}/message_post"

        # Set subtype based on whether it's internal or external
        subtype_xmlid = "mail.mt_note" if is_internal else "mail.mt_comment"

        # Parameters go at TOP LEVEL of request
        payload = {
            "ids": [ticket_id],
            "body": log_message,
            "message_type": "comment",
            "subtype_xmlid": subtype_xmlid,
        }

        try:
            log_type = "internal log" if is_internal else "customer message"
            logger.debug(f"Adding {log_type} to ticket {ticket_id}: {log_message}")
            response = self.post(endpoint, json=payload)
            result = response.json()

            if result:
                logger.info(f"Added {log_type} to ticket {ticket_id}")
                return True

            logger.error(f"Failed to add {log_type}: {result}")
            return False

        except Exception as e:
            logger.error(f"Failed to add log to ticket {ticket_id}: {str(e)}")
            return False

    def update_stage(self, ticket_id: int, stage_id: int) -> bool:
        """Update ticket stage.

        Args:
            ticket_id: Ticket ID
            stage_id: New stage ID

        Returns:
            True if successful
        """
        # JSON-2 API endpoint: POST /json/2/helpdesk.ticket/write
        endpoint = f"/{self.MODEL_NAME}/write"

        # Parameters go at TOP LEVEL of request
        # Note: Odoo's write() method expects 'vals', not 'values'
        payload = {
            "ids": [ticket_id],
            "vals": {
                "stage_id": stage_id,
            },
        }

        try:
            logger.debug(f"Updating ticket {ticket_id} stage to {stage_id}")
            response = self.post(endpoint, json=payload)
            result = response.json()

            if result is True or result == 1:  # Odoo returns True or record count
                logger.info(f"Updated ticket {ticket_id} stage to {stage_id}")
                return True

            logger.error(f"Failed to update stage: {result}")
            return False

        except Exception as e:
            logger.error(f"Failed to update stage for ticket {ticket_id}: {str(e)}")
            return False

    def _parse_ticket(self, ticket_data: Dict[str, Any]) -> Ticket:
        """Parse Odoo ticket data into Ticket model.

        Args:
            ticket_data: Raw ticket data from Odoo API

        Returns:
            Ticket model instance

        Raises:
            ValueError: If ticket data is invalid
        """
        try:
            # Validate required fields
            if not ticket_data.get("id"):
                raise ValueError("Ticket missing required field: id")

            # Use partner_email, default to empty string if not provided
            # Some tickets may not have a customer email
            partner_email = ticket_data.get("partner_email") or ""

            # Parse dates
            create_date = None
            if ticket_data.get("create_date"):
                try:
                    date_str = ticket_data["create_date"]
                    # Handle ISO format with or without Z
                    if isinstance(date_str, str):
                        date_str = date_str.replace("Z", "+00:00")
                        create_date = datetime.fromisoformat(date_str)
                except (ValueError, AttributeError):
                    pass

            write_date = None
            if ticket_data.get("write_date"):
                try:
                    date_str = ticket_data["write_date"]
                    if isinstance(date_str, str):
                        date_str = date_str.replace("Z", "+00:00")
                        write_date = datetime.fromisoformat(date_str)
                except (ValueError, AttributeError):
                    pass

            # Parse many-to-one fields (Odoo returns [id, name])
            def extract_id(field_value):
                """Extract ID from many-to-one field."""
                if isinstance(field_value, list) and len(field_value) > 0:
                    return field_value[0]
                return field_value

            ticket = Ticket(
                id=ticket_data["id"],
                name=ticket_data.get("name", ""),
                email_from=partner_email,  # Map partner_email to email_from
                description=ticket_data.get("description"),
                stage_id=extract_id(ticket_data.get("stage_id")),
                partner_id=extract_id(ticket_data.get("partner_id")),
                create_date=create_date,
                write_date=write_date,
                priority=ticket_data.get("priority", 0),
            )

            return ticket

        except Exception as e:
            logger.error(f"Failed to parse ticket data: {str(e)}")
            raise ValueError(f"Invalid ticket data: {str(e)}")
