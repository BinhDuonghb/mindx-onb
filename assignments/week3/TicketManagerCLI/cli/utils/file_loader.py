"""Utility for loading document content from files."""
from pathlib import Path


class FileLoadError(Exception):
    """Exception raised when file loading fails."""
    pass


class FileLoader:
    """Handle reading and validating document content from files."""

    @staticmethod
    def load_file(file_path: str) -> str:
        """
        Load content from a file.

        Args:
            file_path: Path to the file to load.

        Returns:
            File content as string.

        Raises:
            FileLoadError: If file doesn't exist, can't be read, or is empty.
        """
        try:
            path = Path(file_path)

            # Check if file exists
            if not path.exists():
                raise FileLoadError(f"File not found: {file_path}")

            # Check if it's a file (not directory)
            if not path.is_file():
                raise FileLoadError(f"Path is not a file: {file_path}")

            # Read the file
            content = path.read_text(encoding="utf-8")

            # Check if file is empty
            if not content.strip():
                raise FileLoadError(f"File is empty: {file_path}")

            return content

        except FileLoadError:
            raise
        except Exception as e:
            raise FileLoadError(f"Error reading file {file_path}: {str(e)}")

    @staticmethod
    def extract_title_from_filename(file_path: str) -> str:
        """
        Extract a title from the filename (without extension).

        Args:
            file_path: Path to the file.

        Returns:
            Filename without extension, converted to title case.
        """
        path = Path(file_path)
        filename = path.stem  # Get filename without extension

        # Convert snake_case or kebab-case to Title Case
        title = filename.replace("_", " ").replace("-", " ").title()

        return title
