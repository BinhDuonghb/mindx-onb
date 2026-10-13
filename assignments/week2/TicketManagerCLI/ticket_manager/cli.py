import argparse
import json
from uuid import UUID

from ticket_manager.config import TICKETS_FILE, TEST_TICKETS_FILE
from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.seed_data import get_seed_data
from ticket_manager.services.ticketService import TicketService


def get_tickets_file(use_test: bool):
    """Return the appropriate tickets file path based on test flag."""
    return TEST_TICKETS_FILE if use_test else TICKETS_FILE


def handle_db_error(error: Exception, operation: str = "database") -> int:
    """Handle database errors and return appropriate exit code with user-friendly message."""
    if isinstance(error, json.JSONDecodeError):
        print(f"Error: The {operation} file is corrupted (invalid JSON).")
        print("Please fix the JSON format or restore from a backup.")
        return 1
    elif isinstance(error, FileNotFoundError):
        print(f"Error: The {operation} file not found.")
        print("Initialize it with: tickets create --load-seed-data")
        return 1
    else:
        # Re-raise unexpected errors
        raise




def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tickets",
        description="Ticket Manager CLI",
        epilog="Use 'tickets <command> -h' for help on a specific command"
    )

    # Global flag for test mode
    parser.add_argument(
        "-t", "--test",
        action="store_true",
        help="Use test database instead of production database"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands"
    )

    # CREATE command
    create_parser = subparsers.add_parser(
        "create",
        help="Create a new ticket",
        epilog="""
Examples:
  tickets create --title "Fix login bug"
  tickets create --title "New feature" --description "Add dark mode" --priority high
  tickets create --title "Bug" --tags "frontend,urgent" --priority high
  tickets create --title "Task" --creator "dev@example.com" --assignee "qa@example.com" --estimated_time 5.5
  tickets create --load-seed-data                              # Load sample tickets
        """
    )
    create_parser.add_argument(
        "--title",
        required=False,
        help="Ticket title (required unless --load-seed-data is used)"
    )
    create_parser.add_argument(
        "--description",
        default="",
        help="Ticket description (optional, default: empty)"
    )
    create_parser.add_argument(
        "--priority",
        choices=["low", "medium", "high"],
        default="medium",
        help="Ticket priority (optional, default: medium)"
    )
    create_parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (optional, default: empty)"
    )
    create_parser.add_argument(
        "--creator",
        default="",
        help="Email of who created the task (optional)"
    )
    create_parser.add_argument(
        "--assignee",
        default="",
        help="Email of who will do the task (optional)"
    )
    create_parser.add_argument(
        "--estimated_time",
        type=float,
        default=None,
        help="Estimated time in hours (optional)"
    )
    create_parser.add_argument(
        "--load-seed-data",
        action="store_true",
        help="Load sample/seed tickets (ignores other options)"
    )

    # LIST command
    list_parser = subparsers.add_parser(
        "list",
        help="List tickets with optional filters",
        epilog="""
Examples:
  tickets list                              # List all tickets
  tickets list --status open                # List open tickets
  tickets list --priority high              # List high priority tickets
  tickets list --tag bug                    # List tickets with 'bug' tag
  tickets list --status open --priority high # Combine filters
        """
    )
    list_parser.add_argument(
        "--status",
        choices=["open", "in-progress", "closed"],
        help="Filter by status (optional)"
    )
    list_parser.add_argument(
        "--priority",
        choices=["low", "medium", "high"],
        help="Filter by priority (optional)"
    )
    list_parser.add_argument(
        "--tag",
        help="Filter by tag (optional)"
    )

    # SHOW command
    show_parser = subparsers.add_parser(
        "show",
        help="Show ticket details",
        epilog="""
Examples:
  tickets show 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9
  tickets show 550e8400-e29b-41d4-a716-446655440000
        """
    )
    show_parser.add_argument(
        "id",
        help="Ticket UUID (required)"
    )

    # UPDATE command
    update_parser = subparsers.add_parser(
        "update",
        help="Update ticket status",
        epilog="""
Examples:
  tickets update 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9 --status closed
  tickets update 550e8400-e29b-41d4-a716-446655440000 --status in-progress
        """
    )
    update_parser.add_argument(
        "id",
        help="Ticket UUID (required)"
    )
    update_parser.add_argument(
        "--status",
        required=True,
        choices=["open", "in-progress", "closed"],
        help="New ticket status (required)"
    )

    # DELETE command
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a ticket",
        epilog="""
Examples:
  tickets delete 1c94e7a6-63d7-4ab9-b2ab-12b43dd741b9
  tickets delete 550e8400-e29b-41d4-a716-446655440000
        """
    )
    delete_parser.add_argument(
        "id",
        help="Ticket UUID (required)"
    )

    return parser


def handle_create(parsed_args, use_test: bool = False) -> int:
    """Handle create command."""
    try:
        tickets_file = get_tickets_file(use_test)
        db_client = DBClient(tickets_file)
        ticket_service = TicketService(db_client)

        # Handle seed data loading
        if parsed_args.load_seed_data:
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

        # Handle regular ticket creation
        if not parsed_args.title:
            print("Error: --title is required (unless --load-seed-data is used)")
            return 1

        tags = [
            tag.strip()
            for tag in parsed_args.tags.split(",")
            if tag.strip()
        ]

        # Convert empty strings to None for optional email fields
        creator = parsed_args.creator if parsed_args.creator else None
        assignee = parsed_args.assignee if parsed_args.assignee else None

        ticket = Ticket(
            id=None,
            title=parsed_args.title,
            description=parsed_args.description,
            priority=parsed_args.priority,
            tags=tags,
            creator=creator,
            assignee=assignee,
            estimated_time=parsed_args.estimated_time
        )

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
        return handle_db_error(e, "tickets")


def handle_list(parsed_args, use_test: bool = False) -> int:
    """Handle list command."""
    try:
        tickets_file = get_tickets_file(use_test)
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
        return handle_db_error(e, "tickets")


def handle_show(parsed_args, use_test: bool = False) -> int:
    """Handle show command."""
    try:
        try:
            ticket_id = UUID(parsed_args.id)
        except ValueError:
            print(f"Error: Invalid UUID format: {parsed_args.id}")
            return 1

        tickets_file = get_tickets_file(use_test)
        db_client = DBClient(tickets_file)
        ticket_service = TicketService(db_client)

        ticket = ticket_service.get_by_id(ticket_id)

        if not ticket:
            print(f"Error: Ticket with ID {ticket_id} not found")
            return 1

        # Display ticket details
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

        return 0

    except (json.JSONDecodeError, FileNotFoundError) as e:
        return handle_db_error(e, "tickets")


def handle_update(parsed_args, use_test: bool = False) -> int:
    """Handle update command."""
    try:
        try:
            ticket_id = UUID(parsed_args.id)
        except ValueError:
            print(f"Error: Invalid UUID format: {parsed_args.id}")
            return 1

        tickets_file = get_tickets_file(use_test)
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
        return handle_db_error(e, "tickets")


def handle_delete(parsed_args, use_test: bool = False) -> int:
    """Handle delete command."""
    try:
        try:
            ticket_id = UUID(parsed_args.id)
        except ValueError:
            print(f"Error: Invalid UUID format: {parsed_args.id}")
            return 1

        tickets_file = get_tickets_file(use_test)
        db_client = DBClient(tickets_file)
        ticket_service = TicketService(db_client)

        try:
            ticket_service.delete(ticket_id)
            print(f"Ticket {ticket_id} deleted successfully.")
            return 0
        except ValueError as e:
            print(f"Error: {str(e)}")
            return 1

    except (json.JSONDecodeError, FileNotFoundError) as e:
        return handle_db_error(e, "tickets")


def run_cli(args=None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        return 0

    use_test = getattr(parsed_args, 'test', False)

    if parsed_args.command == "create":
        return handle_create(parsed_args, use_test)

    if parsed_args.command == "list":
        return handle_list(parsed_args, use_test)

    if parsed_args.command == "show":
        return handle_show(parsed_args, use_test)

    if parsed_args.command == "update":
        return handle_update(parsed_args, use_test)

    if parsed_args.command == "delete":
        return handle_delete(parsed_args, use_test)

    return 1
