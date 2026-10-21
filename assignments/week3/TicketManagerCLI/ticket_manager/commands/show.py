"""Show command handler."""
import json
from uuid import UUID

from ticket_manager.config import TICKETS_FILE, TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.services.ticketService import TicketService
from ticket_manager.commands.base import BaseCommand


class ShowCommand(BaseCommand):
    """Handle showing ticket details."""

    def get_tickets_file(self, use_test: bool) -> str:
        """Return the appropriate tickets file path."""
        return TEST_TICKETS_FILE if use_test else TICKETS_FILE

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute show command."""
        try:
            try:
                ticket_id = UUID(parsed_args.id)
            except ValueError:
                print(f"Error: Invalid UUID format: {parsed_args.id}")
                return 1

            tickets_file = self.get_tickets_file(use_test)
            db_client = DBClient(tickets_file)
            ticket_service = TicketService(db_client)

            ticket = ticket_service.get_by_id(ticket_id)

            if not ticket:
                print(f"Error: Ticket with ID {ticket_id} not found")
                return 1

            self._display_ticket(ticket)
            return 0

        except (json.JSONDecodeError, FileNotFoundError) as e:
            return self.handle_db_error(e, "tickets")

    def _display_ticket(self, ticket) -> None:
        """Display ticket details."""
        print(f"\nTicket Details:\n")
        print(f"ID: {ticket.id}")
        print(f"Title: {ticket.title}")
        print(f"Description: {ticket.description}")
        print(f"Status: {ticket.status}")
        print(f"Priority: {ticket.priority}")
        print(f"Tags: {', '.join(ticket.tags) if ticket.tags else 'None'}")
        print(f"Created: {ticket.created_at}")
        print(f"Creator: {ticket.creator if ticket.creator else 'None'}")
        print(f"Assignee: {ticket.assignee if ticket.assignee else 'None'}")
        print(f"Estimated Time: {ticket.estimated_time if ticket.estimated_time else 'None'} hours")
