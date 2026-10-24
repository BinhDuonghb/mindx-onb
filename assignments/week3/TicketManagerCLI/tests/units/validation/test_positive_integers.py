"""Unit tests for PositiveIntegerValidator."""
import pytest

from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator


class TestPositiveIntegerValidatorIsValid:
    """Test PositiveIntegerValidator.is_valid() method."""

    def test_is_valid_positive_one(self):
        """Should accept 1 as positive."""
        assert PositiveIntegerValidator.is_valid(1) is True

    def test_is_valid_positive_large_number(self):
        """Should accept large positive integer."""
        assert PositiveIntegerValidator.is_valid(1000000) is True

    def test_is_valid_positive_small_number(self):
        """Should accept small positive integer."""
        assert PositiveIntegerValidator.is_valid(5) is True

    def test_is_valid_zero_returns_false(self):
        """Should reject zero."""
        assert PositiveIntegerValidator.is_valid(0) is False

    def test_is_valid_negative_one_returns_false(self):
        """Should reject -1."""
        assert PositiveIntegerValidator.is_valid(-1) is False

    def test_is_valid_negative_large_returns_false(self):
        """Should reject large negative integer."""
        assert PositiveIntegerValidator.is_valid(-1000) is False

    def test_is_valid_float_returns_false(self):
        """Should reject float."""
        assert PositiveIntegerValidator.is_valid(1.5) is False

    def test_is_valid_string_returns_false(self):
        """Should reject string."""
        assert PositiveIntegerValidator.is_valid("5") is False

    def test_is_valid_none_returns_false(self):
        """Should reject None."""
        assert PositiveIntegerValidator.is_valid(None) is False

    def test_is_valid_empty_list_returns_false(self):
        """Should reject list."""
        assert PositiveIntegerValidator.is_valid([]) is False

    def test_is_valid_bool_true_returns_true(self):
        """Should accept bool True (subclass of int in Python)."""
        # In Python, bool is a subclass of int, so True == 1
        assert PositiveIntegerValidator.is_valid(True) is True

    def test_is_valid_bool_false_returns_false(self):
        """Should reject bool False (equals 0)."""
        # False == 0, so it fails the > 0 check
        assert PositiveIntegerValidator.is_valid(False) is False


class TestPositiveIntegerValidatorValidate:
    """Test PositiveIntegerValidator.validate() method."""

    def test_validate_positive_integer(self):
        """Should not raise for positive integer."""
        PositiveIntegerValidator.validate(5, "test_param")

    def test_validate_positive_one(self):
        """Should not raise for 1."""
        PositiveIntegerValidator.validate(1, "test_param")

    def test_validate_positive_large(self):
        """Should not raise for large positive integer."""
        PositiveIntegerValidator.validate(999999, "test_param")

    def test_validate_zero_raises_error(self):
        """Should raise ValueError for zero."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            PositiveIntegerValidator.validate(0, "limit")

    def test_validate_zero_includes_param_name(self):
        """Should include parameter name in error message."""
        with pytest.raises(ValueError, match="limit"):
            PositiveIntegerValidator.validate(0, "limit")

    def test_validate_negative_raises_error(self):
        """Should raise ValueError for negative integer."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            PositiveIntegerValidator.validate(-5, "top_k")

    def test_validate_negative_includes_value_in_error(self):
        """Should include the invalid value in error message."""
        with pytest.raises(ValueError, match="-5"):
            PositiveIntegerValidator.validate(-5, "top_k")

    def test_validate_float_raises_error(self):
        """Should raise ValueError for float."""
        with pytest.raises(ValueError, match="must be an integer"):
            PositiveIntegerValidator.validate(1.5, "limit")

    def test_validate_float_includes_type_in_error(self):
        """Should include actual type in error message."""
        with pytest.raises(ValueError, match="float"):
            PositiveIntegerValidator.validate(1.5, "limit")

    def test_validate_string_raises_error(self):
        """Should raise ValueError for string."""
        with pytest.raises(ValueError, match="must be an integer"):
            PositiveIntegerValidator.validate("5", "limit")

    def test_validate_string_includes_type_in_error(self):
        """Should include 'str' in error message."""
        with pytest.raises(ValueError, match="str"):
            PositiveIntegerValidator.validate("5", "limit")

    def test_validate_none_raises_error(self):
        """Should raise ValueError for None."""
        with pytest.raises(ValueError, match="must be an integer"):
            PositiveIntegerValidator.validate(None, "limit")

    def test_validate_list_raises_error(self):
        """Should raise ValueError for list."""
        with pytest.raises(ValueError, match="must be an integer"):
            PositiveIntegerValidator.validate([1, 2, 3], "limit")

    def test_validate_uses_default_param_name(self):
        """Should use default param name 'value' if not provided."""
        with pytest.raises(ValueError, match="value"):
            PositiveIntegerValidator.validate(-1)


class TestPositiveIntegerValidatorValidateAndReturn:
    """Test PositiveIntegerValidator.validate_and_return() method."""

    def test_validate_and_return_positive_integer(self):
        """Should return positive integer as-is."""
        result = PositiveIntegerValidator.validate_and_return(5, "test_param")
        assert result == 5

    def test_validate_and_return_one(self):
        """Should return 1 as-is."""
        result = PositiveIntegerValidator.validate_and_return(1, "test_param")
        assert result == 1

    def test_validate_and_return_large_number(self):
        """Should return large positive integer as-is."""
        result = PositiveIntegerValidator.validate_and_return(999999, "test_param")
        assert result == 999999

    def test_validate_and_return_zero_with_default(self):
        """Should return default when value is zero and default provided."""
        result = PositiveIntegerValidator.validate_and_return(0, "limit", default=10)
        assert result == 10

    def test_validate_and_return_negative_with_default(self):
        """Should return default when value is negative and default provided."""
        result = PositiveIntegerValidator.validate_and_return(-5, "top_k", default=5)
        assert result == 5

    def test_validate_and_return_zero_without_default_raises_error(self):
        """Should raise ValueError for zero without default."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            PositiveIntegerValidator.validate_and_return(0, "limit")

    def test_validate_and_return_negative_without_default_raises_error(self):
        """Should raise ValueError for negative without default."""
        with pytest.raises(ValueError, match="must be a positive integer"):
            PositiveIntegerValidator.validate_and_return(-5, "top_k")

    def test_validate_and_return_invalid_type_without_default_raises_error(self):
        """Should raise ValueError for invalid type without default."""
        with pytest.raises(ValueError, match="must be an integer"):
            PositiveIntegerValidator.validate_and_return("5", "limit")

    def test_validate_and_return_invalid_type_with_default(self):
        """Should return default for invalid type when default provided."""
        result = PositiveIntegerValidator.validate_and_return("5", "limit", default=10)
        assert result == 10

    def test_validate_and_return_default_zero_is_valid(self):
        """Should accept 0 as valid default (different from parameter validation)."""
        # Default value 0 is allowed as a default, even if not valid as parameter
        result = PositiveIntegerValidator.validate_and_return(-5, "limit", default=0)
        assert result == 0

    def test_validate_and_return_default_negative_is_valid(self):
        """Should accept negative as valid default."""
        result = PositiveIntegerValidator.validate_and_return(-5, "limit", default=-10)
        assert result == -10


class TestPositiveIntegerValidatorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_validate_max_int_32bit(self):
        """Should accept max 32-bit integer."""
        PositiveIntegerValidator.validate(2147483647, "param")

    def test_validate_large_64bit_integer(self):
        """Should accept large 64-bit integer."""
        PositiveIntegerValidator.validate(9223372036854775807, "param")

    def test_validate_one_is_minimum_positive(self):
        """Should accept 1 as minimum positive integer."""
        PositiveIntegerValidator.validate(1, "param")

    def test_is_valid_one_is_boundary(self):
        """Should confirm 1 is valid boundary."""
        assert PositiveIntegerValidator.is_valid(1) is True
        assert PositiveIntegerValidator.is_valid(0) is False

    def test_validate_and_return_uses_positional_args(self):
        """Should work with positional arguments."""
        result = PositiveIntegerValidator.validate_and_return(5, "test")
        assert result == 5

    def test_validate_and_return_uses_keyword_args(self):
        """Should work with keyword arguments."""
        result = PositiveIntegerValidator.validate_and_return(
            value=5,
            param_name="test"
        )
        assert result == 5

    def test_validate_and_return_mixed_args(self):
        """Should work with mixed positional and keyword arguments."""
        result = PositiveIntegerValidator.validate_and_return(
            5,
            "test",
            default=10
        )
        assert result == 5


class TestPositiveIntegerValidatorKBContextual:
    """Test contextual usage for KB parameters (--limit, --top-k)."""

    def test_validate_top_k_boundary(self):
        """Should validate top_k with minimum value 1."""
        PositiveIntegerValidator.validate(1, "top_k")

    def test_validate_top_k_typical(self):
        """Should validate typical top_k value of 5."""
        PositiveIntegerValidator.validate(5, "top_k")

    def test_validate_top_k_zero_fails(self):
        """Should reject top_k of 0."""
        with pytest.raises(ValueError, match="top_k"):
            PositiveIntegerValidator.validate(0, "top_k")

    def test_validate_top_k_negative_fails(self):
        """Should reject negative top_k."""
        with pytest.raises(ValueError, match="top_k"):
            PositiveIntegerValidator.validate(-3, "top_k")

    def test_validate_limit_boundary(self):
        """Should validate limit with minimum value 1."""
        PositiveIntegerValidator.validate(1, "limit")

    def test_validate_limit_typical(self):
        """Should validate typical limit value of 10."""
        PositiveIntegerValidator.validate(10, "limit")

    def test_validate_limit_zero_fails(self):
        """Should reject limit of 0."""
        with pytest.raises(ValueError, match="limit"):
            PositiveIntegerValidator.validate(0, "limit")

    def test_validate_limit_negative_fails(self):
        """Should reject negative limit."""
        with pytest.raises(ValueError, match="limit"):
            PositiveIntegerValidator.validate(-10, "limit")

    def test_validate_and_return_apply_default_for_zero_limit(self):
        """Should apply default limit when 0 is passed."""
        # Simulate CLI receiving --limit 0
        result = PositiveIntegerValidator.validate_and_return(
            0,
            "limit",
            default=10
        )
        assert result == 10

    def test_validate_and_return_apply_default_for_zero_top_k(self):
        """Should apply default top_k when 0 is passed."""
        # Simulate CLI receiving --top-k 0
        result = PositiveIntegerValidator.validate_and_return(
            0,
            "top_k",
            default=5
        )
        assert result == 5
