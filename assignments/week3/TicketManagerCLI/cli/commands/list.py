"""List command handler."""
import json

from ticket_manager.config import TICKETS_FILE, TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.services.ticketService import TicketService
from cli.commands.base import BaseCommand


class ListCommand(BaseCommand):
    """Handle listing tickets with optional filters."""

    def get_tickets_file(self, use_test: bool) -> str:
        """Return the appropriate tickets file path."""
        return TEST_TICKETS_FILE if use_test else TICKETS_FILE

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute list command."""
        try:
            tickets_file = self.get_tickets_file(use_test)
            db_client = DBClient(tickets_file)
            ticket_service = TicketService(db_client)

            # Get all tickets
            tickets = ticket_service.get_all()

            # Apply filters
            if parsed_args.status:
                tickets = [t for t in tickets if t.status == parsed_args.status]

            if parsed_args.priority:
                tickets = [t for t in tickets if t.priority == parsed_args.priority]

            if parsed_args.tag:
                tickets = [t for t in tickets if parsed_args.tag in t.tags]

            # Display results
            if not tickets:
                print("No tickets found.")
                return 0

            print(f"\nFound {len(tickets)} ticket(s):\n")
            for ticket in tickets:
                print(f"ID: {ticket.id}")
                print(f"Title: {ticket.title}")
                print(f"Status: {ticket.status}")
                print(f"Priority: {ticket.priority}")
                if ticket.tags:
                    print(f"Tags: {', '.join(ticket.tags)}")
                print("-" * 50)

            return 0

        except (json.JSONDecodeError, FileNotFoundError) as e:
            return self.handle_db_error(e, "tickets")
