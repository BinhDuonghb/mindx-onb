"""Create command handler."""
import json
from uuid import UUID

from ticket_manager.config import TICKETS_FILE, TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.seed_data import get_seed_data
from ticket_manager.services.ticketService import TicketService
from cli.commands.base import BaseCommand


class CreateCommand(BaseCommand):
    """Handle ticket creation."""

    def get_tickets_file(self, use_test: bool) -> str:
        """Return the appropriate tickets file path."""
        return TEST_TICKETS_FILE if use_test else TICKETS_FILE

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute create command."""
        try:
            tickets_file = self.get_tickets_file(use_test)
            db_client = DBClient(tickets_file)
            ticket_service = TicketService(db_client)

            # Handle seed data loading
            if parsed_args.load_seed_data:
                return self._load_seed_data(ticket_service)

            # Handle regular ticket creation
            if not parsed_args.title:
                print("Error: --title is required (unless --load-seed-data is used)")
                return 1

            ticket = self._build_ticket(parsed_args)

            try:
                created_ticket = ticket_service.create(ticket)
                print(
                    f"Ticket created successfully "
                    f"with ID: {created_ticket.id}"
                )
                return 0
            except ValueError as e:
                print(f"Error: {str(e)}")
                return 1

        except (json.JSONDecodeError, FileNotFoundError) as e:
            return self.handle_db_error(e, "tickets")

    def _load_seed_data(self, ticket_service: TicketService) -> int:
        """Load seed data tickets."""
        seed_tickets = get_seed_data()
        created_count = 0

        for ticket in seed_tickets:
            try:
                ticket_service.create(ticket)
                created_count += 1
            except ValueError as e:
                print(f"Error creating seed ticket '{ticket.title}': {str(e)}")

        print(f"\nSuccessfully loaded {created_count}/{len(seed_tickets)} seed tickets.")
        return 0

    def _build_ticket(self, parsed_args) -> Ticket:
        """Build a Ticket object from parsed arguments."""
        tags = [
            tag.strip()
            for tag in parsed_args.tags.split(",")
            if tag.strip()
        ]

        creator = parsed_args.creator if parsed_args.creator else None
        assignee = parsed_args.assignee if parsed_args.assignee else None

        return Ticket(
            id=None,
            title=parsed_args.title,
            description=parsed_args.description,
            priority=parsed_args.priority,
            tags=tags,
            creator=creator,
            assignee=assignee,
            estimated_time=parsed_args.estimated_time
        )
