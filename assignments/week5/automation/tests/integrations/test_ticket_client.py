"""Integration tests for Ticket Client (Odoo JSON-2 API).

These tests verify that TicketClient correctly calls the Odoo JSON-2 API
and parses responses according to the actual API contract.

JSON-2 API responses are direct results, not wrapped in {"jsonrpc": "2.0", "result": ...}
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock
from srcs.clients.odoo.ticket_client import TicketClient
from srcs.models import Ticket
from srcs.config import ODOO_API_ENDPOINT, ODOO_HEADERS, ODOO_DATABASE


class TestTicketClientSearch:
    """Test ticket search functionality."""

    def test_search_tickets_by_domain(self):
        """Should search for tickets matching domain criteria."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        # Mock the POST request - JSON-2 returns direct list, not wrapped
        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = [1, 2, 3, 4, 5]  # Direct ticket IDs
            mock_post.return_value = mock_response

            # Search for tickets in "New" stage
            ticket_ids = client.search_tickets(
                domain=[("stage_id.name", "=", "New")],
                limit=100,
            )

        assert len(ticket_ids) == 5
        assert ticket_ids == [1, 2, 3, 4, 5]

        # Verify the API was called with correct payload
        call_args = mock_post.call_args
        assert call_args[0][0] == "/helpdesk.ticket/search"
        payload = call_args[1]["json"]
        assert payload["domain"] == [("stage_id.name", "=", "New")]
        assert payload["limit"] == 100

    def test_search_tickets_with_pagination(self):
        """Should support pagination with offset."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = [6, 7, 8, 9, 10]
            mock_post.return_value = mock_response

            # Get second page (offset 5)
            ticket_ids = client.search_tickets(
                domain=[],
                limit=5,
                offset=5,
            )

        assert ticket_ids == [6, 7, 8, 9, 10]

        # Verify offset parameter was sent
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["offset"] == 5
        assert payload["limit"] == 5

    def test_search_tickets_empty_result(self):
        """Should return empty list when no tickets found."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_post.return_value = mock_response

            ticket_ids = client.search_tickets(domain=[("id", "=", 999)])

        assert ticket_ids == []

    def test_search_tickets_without_domain(self):
        """Should search all tickets when domain is None."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = [1, 2, 3]
            mock_post.return_value = mock_response

            ticket_ids = client.search_tickets()

        # Verify post was called with empty domain
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["domain"] == []


class TestTicketClientRead:
    """Test ticket read functionality."""

    def test_read_tickets_with_fields(self):
        """Should read specific fields from tickets."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        # Realistic Odoo JSON-2 response with partner_email (not email_from)
        ticket_data = [
            {
                "id": 1,
                "name": "Cannot login",
                "partner_email": "user1@company.com",  # Odoo field name
                "description": "Account locked after inactivity",
                "stage_id": [1, "New"],
                "partner_id": [10, "User One"],
                "create_date": "2024-01-15T10:30:00",
                "priority": "1",  # String selection in Odoo
            }
        ]

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = ticket_data
            mock_post.return_value = mock_response

            tickets = client.read_tickets(
                ticket_ids=[1],
                fields=["id", "name", "partner_email", "stage_id"],
            )

        assert len(tickets) == 1
        assert tickets[0]["id"] == 1
        assert tickets[0]["name"] == "Cannot login"
        assert tickets[0]["partner_email"] == "user1@company.com"

    def test_read_tickets_default_fields(self):
        """Should use default fields if not specified."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = [
            {
                "id": 1,
                "name": "Login Issue",
                "partner_email": "user@company.com",
                "description": "Cannot access account",
                "stage_id": [1, "New"],
                "partner_id": [10, "User"],
                "create_date": "2024-01-15T10:30:00",
                "write_date": "2024-01-15T10:30:00",
                "priority": "1",
            }
        ]

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = ticket_data
            mock_post.return_value = mock_response

            tickets = client.read_tickets(ticket_ids=[1])

        assert len(tickets) == 1

        # Verify default fields were requested
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert "partner_email" in payload["fields"]  # Should request partner_email, not email_from

    def test_read_multiple_tickets(self):
        """Should read multiple tickets in one call."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = [
            {"id": 1, "name": "Ticket 1", "partner_email": "user1@company.com"},
            {"id": 2, "name": "Ticket 2", "partner_email": "user2@company.com"},
            {"id": 3, "name": "Ticket 3", "partner_email": "user3@company.com"},
        ]

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = ticket_data
            mock_post.return_value = mock_response

            tickets = client.read_tickets(ticket_ids=[1, 2, 3])

        assert len(tickets) == 3


class TestTicketClientSingleTicket:
    """Test getting a single ticket."""

    def test_get_ticket_found(self):
        """Should parse ticket data into Ticket model."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = {
            "id": 42,
            "name": "Account Locked",
            "partner_email": "john@company.com",
            "description": "I cannot login to my account",
            "stage_id": [1, "New"],
            "partner_id": [100, "John Doe"],
            "create_date": "2024-01-15T10:30:00",
            "write_date": "2024-01-15T10:30:00",
            "priority": "2",
        }

        with patch.object(client, "read_tickets") as mock_read:
            mock_read.return_value = [ticket_data]

            ticket = client.get_ticket(42)

        assert ticket is not None
        assert isinstance(ticket, Ticket)
        assert ticket.id == 42
        assert ticket.name == "Account Locked"
        assert ticket.email_from == "john@company.com"  # Model uses email_from, mapped from partner_email

    def test_get_ticket_not_found(self):
        """Should return None when ticket not found."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "read_tickets") as mock_read:
            mock_read.return_value = []

            ticket = client.get_ticket(999)

        assert ticket is None


class TestTicketClientAddLog:
    """Test adding logs/messages to tickets."""

    def test_add_log_internal(self):
        """Should add internal log (not sent to customer)."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = True
            mock_post.return_value = mock_response

            success = client.add_log(
                ticket_id=42,
                log_message="[Automation] Internal note",
            )

        assert success.is_success()

        # Verify the API was called with correct internal message payload
        call_args = mock_post.call_args
        assert call_args[0][0] == "/helpdesk.ticket/message_post"
        payload = call_args[1]["json"]
        assert payload["ids"] == [42]
        assert payload["body"] == "[Automation] Internal note"
        assert payload["subtype_xmlid"] == "mail.mt_note"  # Internal


class TestTicketClientParseTicket:
    """Test ticket data parsing."""

    def test_parse_ticket_with_dates(self):
        """Should parse ticket with ISO format dates."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = {
            "id": 1,
            "name": "Test Ticket",
            "partner_email": "test@company.com",
            "description": "Test description",
            "stage_id": [1, "New"],
            "partner_id": [10, "Partner"],
            "create_date": "2024-01-15T10:30:00",
            "write_date": "2024-01-15T14:45:00",
            "priority": "1",
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.id == 1
        assert ticket.create_date is not None
        assert ticket.write_date is not None
        assert isinstance(ticket.create_date, datetime)

    def test_parse_ticket_handles_many_to_one_fields(self):
        """Should handle Odoo many-to-one fields (returned as [id, name])."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = {
            "id": 1,
            "name": "Test",
            "partner_email": "test@company.com",
            "stage_id": [5, "In Progress"],  # Many-to-one field
            "partner_id": [20, "Customer Name"],  # Many-to-one field
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.stage_id == 5
        assert ticket.partner_id == 20
        # category_id removed - doesn't exist in Odoo

    def test_parse_ticket_with_missing_optional_fields(self):
        """Should handle missing optional fields gracefully."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = {
            "id": 1,
            "name": "Minimal Ticket",
            "partner_email": "test@company.com",
            # Missing optional fields: description, stage_id, etc.
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.id == 1
        assert ticket.name == "Minimal Ticket"
        assert ticket.description is None
        assert ticket.stage_id is None

    def test_parse_ticket_with_missing_email(self):
        """Should handle tickets with missing customer email."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = {
            "id": 1,
            "name": "No Email Ticket",
            # partner_email missing or empty
            "stage_id": [1, "New"],
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.id == 1
        assert ticket.email_from == ""  # Empty email is valid

    def test_parse_ticket_with_many_to_one_false_value(self):
        """Should handle Odoo False value for unset many-to-one fields."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = {
            "id": 1,
            "name": "Test",
            "partner_email": "test@company.com",
            "stage_id": False,  # Unset many-to-one
            "partner_id": False,  # Unset many-to-one
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.stage_id is False
        assert ticket.partner_id is False


class TestTicketClientUpdateStage:
    """Test updating ticket stage."""

    def test_update_stage_success(self):
        """Should update ticket stage successfully."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = True
            mock_post.return_value = mock_response

            success = client.update_stage(ticket_id=42, stage_id=2)

        assert success.is_success()

        # Verify the API was called with correct payload using 'vals'
        call_args = mock_post.call_args
        assert call_args[0][0] == "/helpdesk.ticket/write"
        payload = call_args[1]["json"]
        assert payload["ids"] == [42]
        assert payload["vals"] == {"stage_id": 2}  # Note: 'vals', not 'values'

    def test_update_stage_failure(self):
        """Should handle stage update failure."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = False
            mock_post.return_value = mock_response

            success = client.update_stage(ticket_id=42, stage_id=2)

        assert success.is_failure()


class TestTicketClientErrorHandling:
    """Test error handling and resilience."""

    def test_search_handles_api_error(self):
        """Should handle API errors gracefully."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_post.side_effect = Exception("API Connection Error")

            ticket_ids = client.search_tickets()

        assert ticket_ids == []

    def test_read_handles_malformed_response(self):
        """Should handle malformed API responses."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"error": "Invalid request"}
            mock_post.return_value = mock_response

            tickets = client.read_tickets(ticket_ids=[1])

        # Error response is treated as invalid data
        assert tickets == []

    def test_parse_ticket_with_invalid_data(self):
        """Should raise ValueError for invalid ticket data."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        invalid_ticket_data = {
            # Missing required fields
            "description": "No ID or email",
        }

        with pytest.raises(ValueError):
            client._parse_ticket(invalid_ticket_data)

    def test_add_log_handles_api_error(self):
        """Should handle add_log API errors gracefully."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_post.side_effect = Exception("API error")

            success = client.add_log(ticket_id=42, log_message="Test")

        assert success.is_unknown()  # Unexpected exception cannot prove remote non-execution
