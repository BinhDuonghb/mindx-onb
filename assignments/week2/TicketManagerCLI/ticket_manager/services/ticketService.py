from typing import List, Optional
from uuid import UUID, uuid4

from data.db_client import DBClient
from ticket_manager.models.ticket import Ticket
from ticket_manager.validators.ticket_validator import TicketValidator


class TicketService:
    """Service layer for managing tickets using DBClient."""

    def __init__(self, db_client: DBClient):
        """
        Initialize TicketService with a DBClient instance.

        Args:
            db_client: DBClient instance for data persistence.
        """
        self.db_client = db_client

    def create(self, ticket: Ticket) -> Ticket:
        """
        Create a new ticket and persist it.

        Args:
            ticket: Ticket object with title and optional fields.

        Returns:
            The created ticket with generated UUID.

        Raises:
            ValueError: If ticket has invalid data.
        """
        # Validate using TicketValidator
        validator = TicketValidator()

        # Validate required field
        if not ticket.title:
            raise ValueError("Ticket title is required")

        # Validate all fields
        validator.validate_title(ticket.title)
        validator.validate_description(ticket.description)
        validator.validate_priority(ticket.priority)
        validator.validate_status(ticket.status)
        validator.validate_tags(ticket.tags)

        # Validate optional email fields
        if ticket.creator:
            validator.validate_creator(ticket.creator)
        if ticket.assignee:
            validator.validate_assignee(ticket.assignee)

        # Generate UUID
        ticket.id = uuid4()

        # Convert to dict and persist
        ticket_dict = self._ticket_to_dict(ticket)
        self.db_client.write(ticket_dict)

        return ticket

    def get_all(self) -> List[Ticket]:
        """
        Get all tickets.

        Returns:
            List of Ticket objects.
        """
        tickets_data = self.db_client.read()
        return [self._dict_to_ticket(t) for t in tickets_data]

    def get_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        """
        Get a ticket by id.

        Args:
            ticket_id: UUID of the ticket to retrieve.

        Returns:
            Ticket object if found, None otherwise.
        """
        tickets_data = self.db_client.read()
        for ticket_data in tickets_data:
            if UUID(ticket_data.get("id")) == ticket_id:
                return self._dict_to_ticket(ticket_data)
        return None

    def update(self, ticket_id: UUID, **kwargs) -> Ticket:
        """
        Update a ticket by id.

        Args:
            ticket_id: UUID of the ticket to update.
            **kwargs: Fields to update (title, description, status, priority, tags, assignee, estimated_time).

        Returns:
            The updated Ticket object.

        Raises:
            ValueError: If ticket not found or invalid data.
        """
        # Validate update data
        allowed_fields = {"title", "description", "status", "priority", "tags", "assignee", "estimated_time"}
        invalid_fields = set(kwargs.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields: {invalid_fields}")

        if not kwargs:
            raise ValueError("At least one field must be provided for update")

        # Get existing ticket
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket with id {ticket_id} not found")

        # Validate fields being updated
        validator = TicketValidator()

        if "title" in kwargs:
            validator.validate_title(kwargs["title"])
        if "description" in kwargs:
            validator.validate_description(kwargs["description"])
        if "priority" in kwargs:
            validator.validate_priority(kwargs["priority"])
        if "status" in kwargs:
            validator.validate_status(kwargs["status"])
        if "tags" in kwargs:
            validator.validate_tags(kwargs["tags"])
        if "assignee" in kwargs and kwargs["assignee"]:
            validator.validate_assignee(kwargs["assignee"])

        # Update fields
        for key, value in kwargs.items():
            setattr(ticket, key, value)

        # Persist update
        updated_dict = self._ticket_to_dict(ticket)
        self.db_client.update(str(ticket_id), updated_dict)

        return ticket

    def delete(self, ticket_id: UUID) -> None:
        """
        Delete a ticket by id.

        Args:
            ticket_id: UUID of the ticket to delete.

        Raises:
            ValueError: If ticket not found.
        """
        self.db_client.delete(str(ticket_id))

    def get_by_status(self, status: str) -> List[Ticket]:
        """
        Get all tickets with a specific status.

        Args:
            status: Status to filter by (e.g., 'open', 'closed').

        Returns:
            List of Ticket objects with matching status.
        """
        tickets = self.get_all()
        return [t for t in tickets if t.status == status]

    def get_by_priority(self, priority: str) -> List[Ticket]:
        """
        Get all tickets with a specific priority.

        Args:
            priority: Priority to filter by (e.g., 'high', 'medium', 'low').

        Returns:
            List of Ticket objects with matching priority.
        """
        tickets = self.get_all()
        return [t for t in tickets if t.priority == priority]

    @staticmethod
    def _ticket_to_dict(ticket: Ticket) -> dict:
        """Convert Ticket object to dictionary."""
        return {
            "id": str(ticket.id),
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "tags": ticket.tags,
            "created_at": ticket.created_at,
            "creator": ticket.creator,
            "assignee": ticket.assignee,
            "estimated_time": ticket.estimated_time,
        }

    @staticmethod
    def _dict_to_ticket(data: dict) -> Ticket:
        """Convert dictionary to Ticket object."""
        return Ticket(
            id=UUID(data.get("id")) if data.get("id") else None,
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=data.get("status", "open"),
            priority=data.get("priority", "medium"),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            creator=data.get("creator"),
            assignee=data.get("assignee"),
            estimated_time=data.get("estimated_time"),
        )
