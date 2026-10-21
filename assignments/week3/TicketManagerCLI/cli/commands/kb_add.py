"""KB Add command handler."""
import json

from KB.factory import create_kb_client
from KB.models.document import Document
from cli.commands.base import BaseCommand


class KBAddCommand(BaseCommand):
    """Handle KB add command."""

    def __init__(self, kb_client=None):
        """Initialize with KB client (defaults to factory-created client)."""
        self.kb_client = kb_client or create_kb_client()

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute kb add command."""
        try:
            # Parse tags from comma-separated string
            tags = [
                tag.strip()
                for tag in parsed_args.tags.split(",")
                if tag.strip()
            ]

            # Create new document
            new_document = Document(
                id=parsed_args.id,
                title=parsed_args.title,
                content=parsed_args.content,
                node_path=parsed_args.node_path,
                tags=tags,
            )

            try:
                result = self.kb_client.add(new_document)
                print(f"Document added successfully with ID: {result.id}")
                return 0
            except ValueError as e:
                print(f"Error: {str(e)}")
                return 1

        except Exception as e:
            print(f"Error during add: {str(e)}")
            return 1
