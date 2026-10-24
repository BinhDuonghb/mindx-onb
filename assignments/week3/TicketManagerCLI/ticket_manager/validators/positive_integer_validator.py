"""Validator for positive integers used in CLI commands."""


class PositiveIntegerValidator:
    """Validator for positive integer parameters."""

    @staticmethod
    def is_valid(value: int) -> bool:
        """
        Check if value is a positive integer (> 0).

        Args:
            value: Integer value to validate.

        Returns:
            True if value is positive, False otherwise.
        """
        if not isinstance(value, int):
            return False

        return value > 0

    @staticmethod
    def validate(value: int, param_name: str = "value") -> None:
        """
        Validate positive integer and raise ValueError if invalid.

        Args:
            value: Integer value to validate.
            param_name: Name of the parameter (for error messages).

        Raises:
            ValueError: If value is not a positive integer.
        """
        if not isinstance(value, int):
            raise ValueError(
                f"{param_name} must be an integer, got {type(value).__name__}"
            )

        if value <= 0:
            raise ValueError(
                f"{param_name} must be a positive integer (> 0), got {value}"
            )

    @staticmethod
    def validate_and_return(value: int, param_name: str = "value", default: int | None = None) -> int:
        """
        Validate positive integer and return it, or return default if value is invalid.

        Used for CLI arguments where we want to apply a default when value is invalid.

        Args:
            value: Integer value to validate.
            param_name: Name of the parameter (for error messages).
            default: Default value to return if validation fails (if None, raises error).

        Returns:
            The validated value, or default if provided and value is invalid.

        Raises:
            ValueError: If value is invalid and no default is provided.
        """
        if PositiveIntegerValidator.is_valid(value):
            return value

        if default is not None:
            return default

        PositiveIntegerValidator.validate(value, param_name)
        # unreachable, but for type checker
        return value
