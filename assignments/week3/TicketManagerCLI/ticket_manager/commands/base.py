"""Base command class for all CLI commands."""
import json
from abc import ABC, abstractmethod


class BaseCommand(ABC):
    """Base class for all CLI commands."""

    def handle_db_error(self, error: Exception, operation: str = "database") -> int:
        """Handle database errors and return appropriate exit code."""
        if isinstance(error, json.JSONDecodeError):
            print(f"Error: The {operation} file is corrupted (invalid JSON).")
            print("Please fix the JSON format or restore from a backup.")
            return 1
        elif isinstance(error, FileNotFoundError):
            print(f"Error: The {operation} file not found.")
            print("Initialize it with: tickets create --load-seed-data")
            return 1
        else:
            raise

    @abstractmethod
    def execute(self, parsed_args, use_test: bool = False) -> int:
        """Execute the command. Must be implemented by subclasses."""
        pass
