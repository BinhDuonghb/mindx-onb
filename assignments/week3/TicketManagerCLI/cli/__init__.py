"""CLI parser configuration and entry point."""
import argparse

from cli.commands import (
    CreateCommand,
    ListCommand,
    ShowCommand,
    UpdateCommand,
    DeleteCommand,
)
from cli.parsers.ticket_parser import add_ticket_commands


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
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

    # Add ticket and KB commands from separate modules
    add_ticket_commands(subparsers)

    return parser


def run_cli(args=None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        return 0

    use_test = getattr(parsed_args, 'test', False)

    # Map commands to command classes
    commands = {
        "create": CreateCommand(),
        "list": ListCommand(),
        "show": ShowCommand(),
        "update": UpdateCommand(),
        "delete": DeleteCommand(),
    }

    command = commands.get(parsed_args.command)
    if command:
        return command.execute(parsed_args, use_test)

    return 1


__all__ = ["run_cli", "build_parser", "add_ticket_commands"]
