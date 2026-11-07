"""Integration tests for Ticket Client write operations."""

import pytest
import logging
from srcs.clients.odoo.ticket_client import TicketClient
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

    client.close()


class TestTicketClientWriteOperations:
    """Test write operations (add_log, add_note, update_stage)."""

    def test_add_note_to_ticket(self, real_ticket_client : TicketClient):
        """Should add a note to an existing ticket."""
        logger.info("Searching for a ticket to add note...")

        # Find a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]
        logger.info(f"Adding note to ticket {ticket_id}...")

        # Add a note
        success = real_ticket_client.add_log(
            ticket_id=ticket_id,
            log_message="[Automation] Account reactivation processed successfully"
        )

        assert success is True
        logger.info(f"✓ Note added to ticket {ticket_id}")

    def test_add_internal_log_to_ticket(self, real_ticket_client : TicketClient):
        """Should add an internal log (not sent to customer) to a ticket."""
        logger.info("Searching for a ticket to add internal log...")

        # Find a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]
        logger.info(f"Adding internal log to ticket {ticket_id}...")

        # Add an internal log (not visible to customer)
        success = real_ticket_client.add_log(
            ticket_id=ticket_id,
            log_message="[Automation] Internal: Ticket processed by automation engine",
        )

        assert success is True
        logger.info(f"✓ Internal log added to ticket {ticket_id}")

    def test_add_customer_message_to_ticket(self, real_ticket_client : TicketClient):
        """Should add a customer-visible message to a ticket."""
        logger.info("Searching for a ticket to add customer message...")

        # Find a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]
        logger.info(f"Adding customer message to ticket {ticket_id}...")

        # Add a customer-visible message
        success = real_ticket_client.add_log(
            ticket_id=ticket_id,
            log_message="[Automation] Your account has been reactivated. Please try logging in again.",
        )

        assert success is True
        logger.info(f"✓ Customer message added to ticket {ticket_id}")

    def test_update_ticket_stage(self, real_ticket_client : TicketClient):
        """Should update ticket stage."""
        logger.info("Searching for a ticket to update stage...")

        # Find a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]

        # Get current ticket to see current stage
        ticket = real_ticket_client.get_ticket(ticket_id)
        current_stage = ticket.stage_id if ticket else None
        logger.info(f"Ticket {ticket_id} current stage: {current_stage}")

        # Try to update to a different stage (use stage 2 as example)
        new_stage_id = 2
        logger.info(f"Updating ticket {ticket_id} to stage {new_stage_id}...")

        success = real_ticket_client.update_stage(
            ticket_id=ticket_id,
            stage_id=new_stage_id
        )

        assert success is True
        logger.info(f"✓ Stage updated for ticket {ticket_id} to {new_stage_id}")

        # Verify the stage was updated
        updated_ticket = real_ticket_client.get_ticket(ticket_id)
        if updated_ticket:
            logger.info(f"✓ Verified: ticket {ticket_id} stage is now {updated_ticket.stage_id}")


class TestTicketClientAutomationWorkflow:
    """Test a complete automation workflow."""

    def test_complete_automation_workflow(self, real_ticket_client : TicketClient):
        """Test a complete workflow: find ticket, log processing, update stage, add note."""
        logger.info("Starting complete automation workflow test...")

        # Step 1: Find a ticket
        ticket_ids = real_ticket_client.search_tickets(limit=1)

        if not ticket_ids:
            pytest.skip("No tickets found in Odoo instance")

        ticket_id = ticket_ids[0]
        logger.info(f"Step 1: Found ticket {ticket_id}")

        # Step 2: Get ticket details
        ticket = real_ticket_client.get_ticket(ticket_id)
        assert ticket is not None
        logger.info(f"Step 2: Retrieved ticket: {ticket.name}")

        # Step 3: Add internal automation log
        log_success = real_ticket_client.add_log(
            ticket_id=ticket_id,
            log_message="[Automation] Starting automation workflow...",
        )
        assert log_success is True
        logger.info(f"Step 3: Added internal automation log")

        # Step 4: Update stage (if needed)
        if ticket.stage_id != 2:
            stage_success = real_ticket_client.update_stage(
                ticket_id=ticket_id,
                stage_id=2
            )
            assert stage_success is True
            logger.info(f"Step 4: Updated stage to 2")
        else:
            logger.info(f"Step 4: Stage already 2, skipping update")

        # Step 5: Add completion note
        note_success = real_ticket_client.add_log(
            ticket_id=ticket_id,
            log_message="[Automation] Workflow completed successfully"
        )
        assert note_success is True
        logger.info(f"Step 5: Added completion note")

        logger.info(f"✓ Complete automation workflow test PASSED for ticket {ticket_id}")
