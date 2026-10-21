"""Update command handler."""
import json
from uuid import UUID

from ticket_manager.config import TICKETS_FILE, TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.services.ticketService import TicketService
from cli.commands.base import BaseCommand


class UpdateCommand(BaseCommand):
    """Handle updating ticket status."""

    def get_tickets_file(self, use_test: bool) -> str:
        """Return the appropriate tickets file path."""
        return TEST_TICKETS_FILE if use_test else TICKETS_FILE

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute update command."""
        try:
            try:
                ticket_id = UUID(parsed_args.id)
            except ValueError:
                print(f"Error: Invalid UUID format: {parsed_args.id}")
                return 1

            tickets_file = self.get_tickets_file(use_test)
            db_client = DBClient(tickets_file)
            ticket_service = TicketService(db_client)

            try:
                ticket_service.update(ticket_id, status=parsed_args.status)
                print(
                    f"Ticket {ticket_id} updated successfully. "
                    f"Status changed to: {parsed_args.status}"
                )
                return 0
            except ValueError as e:
                print(f"Error: {str(e)}")
                return 1

        except (json.JSONDecodeError, FileNotFoundError) as e:
            return self.handle_db_error(e, "tickets")
