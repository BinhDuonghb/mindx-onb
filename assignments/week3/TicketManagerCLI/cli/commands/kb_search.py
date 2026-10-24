"""KB Search command handler."""
import json

from KB.factory import create_kb_client
from KB.models.search import KBQuery
from cli.commands.base import BaseCommand
from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator


class KBSearchCommand(BaseCommand):
    """Handle KB search command."""

    def __init__(self, kb_client=None):
        """Initialize with KB client (defaults to factory-created client)."""
        self.kb_client = kb_client or create_kb_client()

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute kb search command."""
        try:
            # Validate and apply default for top_k if zero or negative
            top_k = PositiveIntegerValidator.validate_and_return(
                parsed_args.top_k,
                "top_k",
                default=5
            )

            query = KBQuery(
                query=parsed_args.query,
                top_k=top_k
            )

            results = self.kb_client.search(query)

            if not results:
                print(f"No documents found matching: '{parsed_args.query}'")
                return 0

            print(f"\nFound {len(results)} document(s):\n")
            for result in results:
                print(f"ID: {result.id}")
                print(f"Title: {result.title}")
                print(f"Path: {result.node_path}")
                print("-" * 50)

            return 0

        except Exception as e:
            print(f"Error during search: {str(e)}")
            return 1
