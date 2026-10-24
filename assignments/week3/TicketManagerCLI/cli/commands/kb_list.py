"""KB List command handler."""
import json

from KB.factory import create_kb_client
from cli.commands.base import BaseCommand
from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator


class KBListCommand(BaseCommand):
    """Handle KB list command."""

    def __init__(self, kb_client=None):
        """Initialize with KB client (defaults to factory-created client)."""
        self.kb_client = kb_client or create_kb_client()

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute kb list command."""
        try:
            # Validate and apply default for limit if zero or negative
            limit = PositiveIntegerValidator.validate_and_return(
                parsed_args.limit,
                "limit",
                default=10
            )

            documents = self.kb_client.list(
                node_path=parsed_args.node_path,
                limit=limit
            )

            if not documents:
                print("No documents found.")
                return 0

            print(f"\nFound {len(documents)} document(s):\n")
            for doc in documents:
                print(f"ID: {doc.id}")
                print(f"Title: {doc.title}")
                print(f"Path: {doc.node_path}")
                if doc.tags:
                    print(f"Tags: {', '.join(doc.tags)}")
                print("-" * 50)

            return 0

        except Exception as e:
            print(f"Error during list: {str(e)}")
            return 1
