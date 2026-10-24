"""KB Add command handler."""
import json

from KB.factory import create_kb_client
from KB.models.document import Document
from cli.commands.base import BaseCommand
from cli.utils.file_loader import FileLoader, FileLoadError


class KBAddCommand(BaseCommand):
    """Handle KB add command."""

    def __init__(self, kb_client=None):
        """Initialize with KB client (defaults to factory-created client)."""
        self.kb_client = kb_client or create_kb_client()

    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute kb add command."""
        try:
            # Validate content source (--content or --file, not both)
            if parsed_args.content and parsed_args.file:
                print("Error: Cannot use both --content and --file. Choose one.")
                return 1

            if not parsed_args.content and not parsed_args.file:
                print("Error: Must provide either --content or --file.")
                return 1

            # Validate node path source (--node or --path, not both)
            if parsed_args.node_path and parsed_args.path_alias:
                print("Error: Cannot use both --node and --path. Choose one.")
                return 1

            if not parsed_args.node_path and not parsed_args.path_alias:
                print("Error: Must provide either --node or --path.")
                return 1

            # Determine node path
            node_path = parsed_args.node_path or parsed_args.path_alias

            # Determine title and content
            if parsed_args.file:
                # Load content from file
                try:
                    content = FileLoader.load_file(parsed_args.file)
                    # If title not provided, extract from filename
                    title = parsed_args.title or FileLoader.extract_title_from_filename(
                        parsed_args.file
                    )
                except FileLoadError as e:
                    print(f"Error: {str(e)}")
                    return 1
            else:
                # Use direct content
                if not parsed_args.title:
                    print("Error: --title is required when using --content.")
                    return 1
                content = parsed_args.content
                title = parsed_args.title

            # Parse tags from comma-separated string
            tags = [
                tag.strip()
                for tag in parsed_args.tags.split(",")
                if tag.strip()
            ]

            # Create new document
            new_document = Document(
                id=parsed_args.id,
                title=title,
                content=content,
                node_path=node_path,
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
