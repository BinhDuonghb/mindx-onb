import re
from typing import Optional

class EmailValidator:
    """Validator for email addresses."""

    # More strict RFC 5322 pattern for email validation
    # Local part: alphanumeric, dots, underscores, hyphens, plus, percent
    # Domain: alphanumeric, hyphens, dots (but not at start/end)
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    @staticmethod
    def is_valid(email: str) -> bool:
        """
        Check if email is valid.

        Args:
            email: Email string to validate.

        Returns:
            True if email is valid, False otherwise.
        """
        if not email or not isinstance(email, str):
            return False

        email = email.strip()

        # Basic pattern check
        if not re.match(EmailValidator.EMAIL_PATTERN, email):
            return False

        # Additional strict checks
        local_part, domain_part = email.split("@")

        # Check for consecutive dots
        if ".." in email:
            return False

        # Check local part
        if local_part.startswith(".") or local_part.endswith("."):
            return False

        # Check domain part
        if domain_part.startswith(".") or domain_part.endswith("."):
            return False

        # Check for hyphen at start/end of domain labels
        for label in domain_part.split("."):
            if label.startswith("-") or label.endswith("-"):
                return False

        return True

    @staticmethod
    def validate(email: Optional[str]) -> None:
        """
        Validate email and raise ValueError if invalid.

        Args:
            email: Email string to validate (can be None).

        Raises:
            ValueError: If email is provided but invalid.
        """
        if email is None:
            return

        if not isinstance(email, str):
            raise ValueError(f"Email must be a string, got {type(email).__name__}")

        if not email.strip():
            raise ValueError("Email cannot be empty or whitespace only")

        if len(email) > 254:
            raise ValueError(f"Email too long (max 254 characters): {len(email)} characters")

        # Split and validate parts
        if "@" not in email:
            raise ValueError(f"Invalid email format: {email} (missing @)")

        if email.count("@") > 1:
            raise ValueError(f"Invalid email format: {email} (multiple @)")

        local_part, domain_part = email.split("@")

        # Check local part
        if len(local_part) == 0:
            raise ValueError(f"Local part cannot be empty")

        if len(local_part) > 64:
            raise ValueError(f"Local part too long (max 64 characters): {len(local_part)} characters")

        if local_part.startswith("."):
            raise ValueError(f"Local part cannot start with a dot: {local_part}")

        if local_part.endswith("."):
            raise ValueError(f"Local part cannot end with a dot: {local_part}")

        # Check for consecutive dots
        if ".." in email:
            raise ValueError(f"Email cannot contain consecutive dots")

        # Check domain part
        if len(domain_part) == 0:
            raise ValueError("Domain part cannot be empty")

        if domain_part.startswith("."):
            raise ValueError("Domain cannot start with a dot")

        if domain_part.endswith("."):
            raise ValueError("Domain cannot end with a dot")

        # Check domain labels
        domain_labels = domain_part.split(".")
        for label in domain_labels:
            if label.startswith("-"):
                raise ValueError(f"Domain label cannot start with hyphen: {label}")
            if label.endswith("-"):
                raise ValueError(f"Domain label cannot end with hyphen: {label}")

        # Final format check
        if not EmailValidator.is_valid(email):
            raise ValueError(f"Invalid email format: {email}")

