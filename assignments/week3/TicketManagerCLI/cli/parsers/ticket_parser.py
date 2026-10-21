"""Ticket manager command parsers."""


def add_ticket_commands(subparsers):
    """Add ticket manager commands to the parser."""
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
