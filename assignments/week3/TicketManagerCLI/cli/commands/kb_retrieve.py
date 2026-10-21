"""KB Retrieve command handler."""
import json

from KB.factory import create_kb_client
from cli.commands.base import BaseCommand


class KBRetrieveCommand(BaseCommand):
    """Handle KB retrieve command."""

    def __init__(self, kb_client=None):
        """Initialize with KB client (defaults to factory-created client)."""
        self.kb_client = kb_client or create_kb_client()

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute kb retrieve command."""
        try:
            doc_id = parsed_args.id

            try:
                document = self.kb_client.retrieve(doc_id)
            except ValueError as e:
                print(f"Error: {str(e)}")
                return 1

            self._display_document(document)
            return 0

        except Exception as e:
            print(f"Error during retrieve: {str(e)}")
            return 1

    def _display_document(self, document) -> None:
        """Display document details."""
        print(f"\nDocument Details:\n")
        print(f"ID: {document.id}")
        print(f"Title: {document.title}")
        print(f"Path: {document.node_path}")
        print(f"Tags: {', '.join(document.tags) if document.tags else 'None'}")
        print(f"\nContent:\n")
        print(document.content)
        print("\n" + "-" * 50)
