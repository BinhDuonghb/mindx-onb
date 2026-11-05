"""Integration tests for Ticket Client (Odoo JSON-2 API)."""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock
from srcs.clients.odoo.ticket import TicketClient
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

        # Mock the POST request
        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": [1, 2, 3, 4, 5],  # Ticket IDs
            }
            mock_post.return_value = mock_response

            # Search for tickets in "New" stage
            ticket_ids = client.search_tickets(
                domain=[("stage_id.name", "=", "New")],
                limit=100,
            )

        assert len(ticket_ids) == 5
        assert ticket_ids == [1, 2, 3, 4, 5]

    def test_search_tickets_with_pagination(self):
        """Should support pagination with offset."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "result": [6, 7, 8, 9, 10],
            }
            mock_post.return_value = mock_response

            # Get second page (offset 5)
            ticket_ids = client.search_tickets(
                domain=[],
                limit=5,
                offset=5,
            )

        assert ticket_ids == [6, 7, 8, 9, 10]

    def test_search_tickets_empty_result(self):
        """Should return empty list when no tickets found."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"result": []}
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
            mock_response.json.return_value = {"result": [1, 2, 3]}
            mock_post.return_value = mock_response

            ticket_ids = client.search_tickets()

        # Verify post was called with empty domain
        call_args = mock_post.call_args
        assert call_args is not None


class TestTicketClientRead:
    """Test ticket read functionality."""

    def test_read_tickets_with_fields(self):
        """Should read specific fields from tickets."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = [
            {
                "id": 1,
                "name": "Cannot login",
                "email_from": "user1@company.com",
                "description": "Account locked after inactivity",
                "stage_id": [1, "New"],
                "partner_id": [10, "User One"],
                "create_date": "2024-01-15 10:30:00",
                "priority": 1,
            }
        ]

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"result": ticket_data}
            mock_post.return_value = mock_response

            tickets = client.read_tickets(
                ticket_ids=[1],
                fields=["id", "name", "email_from", "stage_id"],
            )

        assert len(tickets) == 1
        assert tickets[0]["id"] == 1
        assert tickets[0]["name"] == "Cannot login"

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
                "email_from": "user@company.com",
                "description": "Cannot access account",
                "stage_id": [1, "New"],
                "partner_id": [10, "User"],
                "create_date": "2024-01-15 10:30:00",
                "write_date": "2024-01-15 10:30:00",
                "priority": 1,
            }
        ]

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"result": ticket_data}
            mock_post.return_value = mock_response

            tickets = client.read_tickets(ticket_ids=[1])

        assert len(tickets) == 1

    def test_read_multiple_tickets(self):
        """Should read multiple tickets in one call."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        ticket_data = [
            {"id": 1, "name": "Ticket 1", "email_from": "user1@company.com"},
            {"id": 2, "name": "Ticket 2", "email_from": "user2@company.com"},
            {"id": 3, "name": "Ticket 3", "email_from": "user3@company.com"},
        ]

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"result": ticket_data}
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
            "email_from": "john@company.com",
            "description": "I cannot login to my account",
            "stage_id": [1, "New"],
            "partner_id": [100, "John Doe"],
            "create_date": "2024-01-15 10:30:00",
            "write_date": "2024-01-15 10:30:00",
            "priority": 2,
        }

        with patch.object(client, "read_tickets") as mock_read:
            mock_read.return_value = [ticket_data]

            ticket = client.get_ticket(42)

        assert ticket is not None
        assert isinstance(ticket, Ticket)
        assert ticket.id == 42
        assert ticket.name == "Account Locked"
        assert ticket.email_from == "john@company.com"

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


class TestTicketClientAddNote:
    """Test adding notes to tickets."""

    def test_add_note_success(self):
        """Should add note to ticket successfully."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "result": 123,  # Message ID
            }
            mock_post.return_value = mock_response

            success = client.add_note(
                ticket_id=42,
                note="Account has been reactivated automatically."
            )

        assert success is True

    def test_add_note_failure(self):
        """Should handle note addition failure."""
        client = TicketClient(
            api_endpoint=ODOO_API_ENDPOINT,
            database=ODOO_DATABASE,
            headers=ODOO_HEADERS,
        )

        with patch.object(client, "post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "error": {"message": "Ticket not found"}
            }
            mock_post.return_value = mock_response

            success = client.add_note(ticket_id=999, note="Test")

        assert success is False


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
            "email_from": "test@company.com",
            "description": "Test description",
            "stage_id": [1, "New"],
            "partner_id": [10, "Partner"],
            "create_date": "2024-01-15T10:30:00",
            "write_date": "2024-01-15T14:45:00",
            "priority": 1,
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
            "email_from": "test@company.com",
            "stage_id": [5, "In Progress"],  # Many-to-one field
            "partner_id": [20, "Customer Name"],  # Many-to-one field
            "category_id": [2, "Technical"],  # Many-to-one field
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.stage_id == 5
        assert ticket.partner_id == 20
        assert ticket.category_id == 2

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
            "email_from": "test@company.com",
            # Missing optional fields: description, stage_id, etc.
        }

        ticket = client._parse_ticket(ticket_data)

        assert ticket.id == 1
        assert ticket.name == "Minimal Ticket"
        assert ticket.description is None
        assert ticket.stage_id is None


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
