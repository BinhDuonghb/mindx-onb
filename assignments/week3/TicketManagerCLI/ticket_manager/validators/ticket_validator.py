from typing import Optional

from ticket_manager.validators.email_validator import EmailValidator


class TicketValidator:
    """Validator for Ticket model."""

    @staticmethod
    def validate_title(title: str) -> None:
        """
        Validate ticket title.

        Args:
            title: Title string to validate.

        Raises:
            ValueError: If title is invalid.
        """
        if not isinstance(title, str):
            raise ValueError(f"Title must be a string, got {type(title).__name__}")

        if not title.strip():
            raise ValueError("Title cannot be empty or whitespace only")

        if len(title) < 3:
            raise ValueError(f"Title too short (min 3 characters): {len(title)} characters")

        if len(title) > 255:
            raise ValueError(f"Title too long (max 255 characters): {len(title)} characters")

    @staticmethod
    def validate_description(description: str) -> None:
        """
        Validate ticket description.

        Args:
            description: Description string to validate.

        Raises:
            ValueError: If description is invalid.
        """
        if not isinstance(description, str):
            raise ValueError(f"Description must be a string, got {type(description).__name__}")

        if len(description) > 5000:
            raise ValueError(f"Description too long (max 5000 characters): {len(description)} characters")

    @staticmethod
    def validate_priority(priority: str) -> None:
        """
        Validate ticket priority.

        Args:
            priority: Priority string to validate.

        Raises:
            ValueError: If priority is invalid.
        """
        valid_priorities = ["low", "medium", "high"]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority: {priority}. Must be one of {valid_priorities}")

    @staticmethod
    def validate_status(status: str) -> None:
        """
        Validate ticket status.

        Args:
            status: Status string to validate.

        Raises:
            ValueError: If status is invalid.
        """
        valid_statuses = ["open", "in-progress", "closed"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

    @staticmethod
    def validate_tags(tags: list) -> None:
        """
        Validate ticket tags.

        Args:
            tags: List of tags to validate.

        Raises:
            ValueError: If tags are invalid.
        """
        if not isinstance(tags, list):
            raise ValueError(f"Tags must be a list, got {type(tags).__name__}")

        if len(tags) > 10:
            raise ValueError(f"Too many tags (max 10): {len(tags)} tags")

        for tag in tags:
            if not isinstance(tag, str):
                raise ValueError(f"Each tag must be a string, got {type(tag).__name__}")

            if not tag.strip():
                raise ValueError("Tag cannot be empty or whitespace only")

            if len(tag) < 2:
                raise ValueError(f"Tag too short (min 2 characters): {len(tag)} characters")

            if len(tag) > 50:
                raise ValueError(f"Tag too long (max 50 characters): {len(tag)} characters")

    @staticmethod
    def validate_creator(creator: Optional[str]) -> None:
        """
        Validate ticket creator email.

        Args:
            creator: Creator email to validate (can be None).

        Raises:
            ValueError: If creator is provided but invalid.
        """
        EmailValidator.validate(creator)

    @staticmethod
    def validate_assignee(assignee: Optional[str]) -> None:
        """
        Validate ticket assignee email.

        Args:
            assignee: Assignee email to validate (can be None).

        Raises:
            ValueError: If assignee is provided but invalid.
        """
        EmailValidator.validate(assignee)
