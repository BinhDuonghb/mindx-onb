"""End-to-End tests for Odoo Ticket Client - Real API calls to actual Odoo instance.

These tests make REAL requests to the Odoo API using TEST_ODOO credentials.
They verify actual integration with the Odoo helpdesk system.

Run with:
    pytest tests/e2e/test_odoo_ticket_client_e2e.py -v -s

Skip these tests:
    pytest tests/e2e/test_odoo_ticket_client_e2e.py --ignore=tests/e2e/
"""

import pytest
import logging
from srcs.clients.odoo.ticket_client import TicketClient
from srcs.models import Ticket
from srcs.config import ACTIVE_ODOO_URL, ACTIVE_ODOO_DATABASE, ACTIVE_ODOO_RPC_KEY

logger = logging.getLogger(__name__)


@pytest.fixture
def real_ticket_client():
    """Create a real TicketClient connected to test Odoo instance."""
    headers = {
        "Authorization": f"Bearer {ACTIVE_ODOO_RPC_KEY}",
        "Content-Type": "application/json",
    }

    api_endpoint = f"{ACTIVE_ODOO_URL}/json/2"

    client = TicketClient(
        api_endpoint=api_endpoint,
        database=ACTIVE_ODOO_DATABASE,
        headers=headers,
        timeout=30,
        max_retries=1,
    )

    logger.info(f"Connected to Odoo: {ACTIVE_ODOO_URL} / {ACTIVE_ODOO_DATABASE}")

    yield client

    # Cleanup
    client.close()


class TestOdooTicketClientRealAPI:
    """Test real ticket operations against actual Odoo instance."""

    def test_search_tickets_returns_results(self, real_ticket_client):
        """Should search for tickets and return IDs from real Odoo."""
        logger.info("Searching for all tickets...")

        # Search for all tickets
        ticket_ids = real_ticket_client.search_tickets(
            domain=[],
            limit=10,
        )

        logger.info(f"Found {len(ticket_ids)} tickets")

        # Should return at least some tickets (or empty list if no tickets)
        assert isinstance(ticket_ids, list)

        if len(ticket_ids) > 0:
            logger.info(f"Ticket IDs: {ticket_ids}")

    def test_search_tickets_with_specific_domain(self, real_ticket_client):
        """Should search for tickets with domain filter."""
        logger.info("Searching for tickets in 'New' stage...")

        # Search for tickets in New stage
        ticket_ids = real_ticket_client.search_tickets(
            domain=[("stage_id.name", "=", "New")],
            limit=5,
        )

        logger.info(f"Found {len(ticket_ids)} tickets in 'New' stage")

        assert isinstance(ticket_ids, list)

    def test_read_tickets_returns_valid_data(self, real_ticket_client):
        """Should read ticket data and return valid Ticket models."""
        logger.info("Searching for a ticket to read...")

        # First, find a ticket ID
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]
        logger.info(f"Reading ticket ID {ticket_id}...")

        # Read the ticket with correct Odoo field name (partner_email, not email_from)
        ticket_data = real_ticket_client.read_tickets(
            ticket_ids=[ticket_id],
            fields=[
                "id", "name", "partner_email", "description",
                "stage_id", "partner_id", "create_date", "priority"
            ]
        )

        assert len(ticket_data) == 1
        logger.info(f"Ticket data: {ticket_data[0]}")

    def test_get_ticket_returns_ticket_model(self, real_ticket_client):
        """Should retrieve a single ticket as Ticket model."""
        logger.info("Searching for a ticket...")

        # Find a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]
        logger.info(f"Getting ticket {ticket_id} as model...")

        # Get as model
        ticket = real_ticket_client.get_ticket(ticket_id)

        assert ticket is not None
        assert isinstance(ticket, Ticket)
        assert ticket.id == ticket_id
        # Email may be empty for some tickets
        if ticket.email_from:
            assert "@" in ticket.email_from, "Email should contain @ if provided"

        logger.info(f"✓ Ticket: {ticket.name}")
        logger.info(f"  ID: {ticket.id}")
        logger.info(f"  Email: {ticket.email_from or 'N/A'}")
        logger.info(f"  Stage: {ticket.stage_id}")

    def test_get_nonexistent_ticket_returns_none(self, real_ticket_client):
        """Should return None for non-existent ticket."""
        logger.info("Attempting to get non-existent ticket ID 999999...")

        ticket = real_ticket_client.get_ticket(999999)

        assert ticket is None
        logger.info("✓ Correctly returned None for non-existent ticket")

    def test_read_multiple_tickets(self, real_ticket_client):
        """Should read multiple tickets in one call."""
        logger.info("Searching for multiple tickets...")

        # Find multiple tickets
        ticket_ids = real_ticket_client.search_tickets(limit=3)

        if len(ticket_ids) < 2:
            pytest.skip("Need at least 2 tickets to test multi-read")

        logger.info(f"Reading {len(ticket_ids)} tickets...")

        # Read all tickets
        tickets_data = real_ticket_client.read_tickets(ticket_ids=ticket_ids)

        assert len(tickets_data) == len(ticket_ids)

        for i, ticket_data in enumerate(tickets_data):
            logger.info(f"  Ticket {i+1}: {ticket_data.get('name', 'N/A')}")

    def test_ticket_fields_are_accessible(self, real_ticket_client):
        """Should have all expected fields on ticket model."""
        logger.info("Verifying ticket model fields...")

        # Get a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket = real_ticket_client.get_ticket(ticket_ids[0])

        # Verify all expected fields exist
        assert hasattr(ticket, "id")
        assert hasattr(ticket, "name")
        assert hasattr(ticket, "email_from")
        assert hasattr(ticket, "description")
        assert hasattr(ticket, "stage_id")
        assert hasattr(ticket, "partner_id")
        assert hasattr(ticket, "create_date")
        assert hasattr(ticket, "priority")
        assert hasattr(ticket, "is_login_issue")
        assert hasattr(ticket, "issue_type")

        logger.info("✓ All expected fields present")
        logger.info(f"  - id: {ticket.id}")
        logger.info(f"  - name: {ticket.name}")
        logger.info(f"  - email_from: {ticket.email_from}")
        logger.info(f"  - stage_id: {ticket.stage_id}")
        logger.info(f"  - create_date: {ticket.create_date}")


class TestOdooTicketClientRealDataValidation:
    """Test data validation with real Odoo data."""

    def test_many_to_one_fields_are_extracted_correctly(self, real_ticket_client):
        """Verify many-to-one fields (stage_id, partner_id) are parsed correctly."""
        logger.info("Testing many-to-one field extraction...")

        ticket_ids = real_ticket_client.search_tickets(limit=1)
        if not ticket_ids:
            pytest.skip("No tickets found")

        # Get raw ticket data
        ticket_data = real_ticket_client.read_tickets(ticket_ids=[ticket_ids[0]])
        raw_data = ticket_data[0]

        logger.info(f"Raw stage_id from API: {raw_data.get('stage_id')}")
        logger.info(f"Raw partner_id from API: {raw_data.get('partner_id')}")

        # Parse into model
        ticket = real_ticket_client._parse_ticket(raw_data)

        # stage_id and partner_id should be integers (extracted from [id, name])
        if ticket.stage_id is not None:
            assert isinstance(ticket.stage_id, int), "stage_id should be int"
            logger.info(f"✓ stage_id correctly extracted as int: {ticket.stage_id}")

        if ticket.partner_id is not None:
            assert isinstance(ticket.partner_id, int), "partner_id should be int"
            logger.info(f"✓ partner_id correctly extracted as int: {ticket.partner_id}")

    def test_dates_are_parsed_correctly(self, real_ticket_client):
        """Verify dates are parsed to datetime objects."""
        from datetime import datetime

        logger.info("Testing date parsing...")

        ticket_ids = real_ticket_client.search_tickets(limit=1)
        if not ticket_ids:
            pytest.skip("No tickets found")

        ticket = real_ticket_client.get_ticket(ticket_ids[0])

        if ticket.create_date:
            assert isinstance(ticket.create_date, datetime)
            logger.info(f"✓ create_date is datetime: {ticket.create_date}")

        if ticket.write_date:
            assert isinstance(ticket.write_date, datetime)
            logger.info(f"✓ write_date is datetime: {ticket.write_date}")

    def test_ticket_model_validation(self, real_ticket_client):
        """Verify Ticket models validate required fields."""
        logger.info("Testing ticket model validation...")

        ticket_ids = real_ticket_client.search_tickets(limit=1)
        if not ticket_ids:
            pytest.skip("No tickets found")

        ticket = real_ticket_client.get_ticket(ticket_ids[0])

        # These should always be set on valid ticket
        assert ticket.id > 0, "Ticket ID should be positive"
        # Email may be empty for some tickets - that's valid
        if ticket.email_from:
            assert "@" in ticket.email_from, "Should be valid email format if provided"

        logger.info(f"✓ Ticket validation passed")
        logger.info(f"  ID: {ticket.id}")
        logger.info(f"  Email: {ticket.email_from or 'N/A'}")
        logger.info(f"  Valid: True")
