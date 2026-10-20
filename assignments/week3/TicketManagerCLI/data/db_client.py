import json
from pathlib import Path
from typing import Any, Dict, List


class DBClient:
    """Client for reading, writing, updating, and deleting tickets from JSON file."""

    def __init__(self, file_path: Path):
        """
        Initialize DBClient with a file path.

        Args:
            file_path: Path object pointing to the JSON file.
        """
        self.file_path = file_path

    def read(self) -> List[Dict[str, Any]]:
        """
        Read all tickets from the JSON file.

        Returns:
            List of ticket dictionaries.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def write(self, ticket: Dict[str, Any]) -> None:
        """
        Write (append) a ticket to the JSON file.

        Args:
            ticket: Ticket dictionary to write.
        """
        # Read existing tickets
        tickets = self.read()

        # Append new ticket
        tickets.append(ticket)

        # Write back to file
        self._write_all(tickets)

    def update(self, ticket_id: int, updated_data: Dict[str, Any]) -> None:
        """
        Update a ticket by id.

        Args:
            ticket_id: ID of the ticket to update.
            updated_data: Dictionary with fields to update.

        Raises:
            ValueError: If ticket with given id is not found.
        """
        tickets = self.read()

        # Find ticket with matching id
        found = False
        for i, ticket in enumerate(tickets):
            if ticket.get("id") == ticket_id:
                # Update only the fields in updated_data
                tickets[i].update(updated_data)
                found = True
                break

        if not found:
            raise ValueError(f"Ticket with id {ticket_id} not found")

        # Write back to file
        self._write_all(tickets)

    def delete(self, ticket_id: int) -> None:
        """
        Delete a ticket by id.

        Args:
            ticket_id: ID of the ticket to delete.

        Raises:
            ValueError: If ticket with given id is not found.
        """
        tickets = self.read()

        # Find and remove ticket
        original_length = len(tickets)
        tickets = [t for t in tickets if t.get("id") != ticket_id]

        if len(tickets) == original_length:
            raise ValueError(f"Ticket with id {ticket_id} not found")

        # Write back to file
        self._write_all(tickets)

    def _write_all(self, tickets: List[Dict[str, Any]]) -> None:
        """
        Write all tickets to the JSON file.

        Args:
            tickets: List of ticket dictionaries.
        """
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
