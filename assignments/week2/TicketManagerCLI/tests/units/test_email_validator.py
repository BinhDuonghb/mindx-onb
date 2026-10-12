import pytest
from ticket_manager.validators.email_validator import EmailValidator


class TestEmailValidatorIsValid:
    """Test EmailValidator.is_valid() method."""

    def test_valid_simple_email(self):
        """Should accept simple valid email."""
        assert EmailValidator.is_valid("user@example.com") is True

    def test_valid_email_with_numbers(self):
        """Should accept email with numbers."""
        assert EmailValidator.is_valid("user123@example.com") is True

    def test_valid_email_with_dots_in_local(self):
        """Should accept email with dots in local part."""
        assert EmailValidator.is_valid("user.name@example.com") is True

    def test_valid_email_with_plus(self):
        """Should accept email with plus sign."""
        assert EmailValidator.is_valid("user+tag@example.com") is True

    def test_valid_email_with_hyphen_in_domain(self):
        """Should accept email with hyphen in domain."""
        assert EmailValidator.is_valid("user@my-example.com") is True

    def test_valid_email_with_subdomain(self):
        """Should accept email with subdomain."""
        assert EmailValidator.is_valid("user@mail.example.com") is True

    def test_valid_email_with_multiple_subdomains(self):
        """Should accept email with multiple subdomains."""
        assert EmailValidator.is_valid("user@mail.co.example.com") is True

    def test_valid_email_with_underscore(self):
        """Should accept email with underscore in local part."""
        assert EmailValidator.is_valid("user_name@example.com") is True

    def test_valid_email_with_percent(self):
        """Should accept email with percent in local part."""
        assert EmailValidator.is_valid("user%tag@example.com") is True

    def test_valid_email_short_domain(self):
        """Should accept email with short domain extension."""
        assert EmailValidator.is_valid("user@example.io") is True

    def test_valid_email_long_domain(self):
        """Should accept email with long domain extension."""
        assert EmailValidator.is_valid("user@example.museum") is True

    def test_valid_email_mixed_case(self):
        """Should accept email with mixed case."""
        assert EmailValidator.is_valid("User@Example.COM") is True

    def test_invalid_email_no_at_symbol(self):
        """Should reject email without @ symbol."""
        assert EmailValidator.is_valid("userexample.com") is False

    def test_invalid_email_multiple_at_symbols(self):
        """Should reject email with multiple @ symbols."""
        assert EmailValidator.is_valid("user@exam@ple.com") is False

    def test_invalid_email_no_domain(self):
        """Should reject email without domain."""
        assert EmailValidator.is_valid("user@") is False

    def test_invalid_email_no_local_part(self):
        """Should reject email without local part."""
        assert EmailValidator.is_valid("@example.com") is False

    def test_invalid_email_no_extension(self):
        """Should reject email without domain extension."""
        assert EmailValidator.is_valid("user@example") is False

    def test_invalid_email_empty_string(self):
        """Should reject empty string."""
        assert EmailValidator.is_valid("") is False

    def test_invalid_email_whitespace(self):
        """Should reject whitespace only."""
        assert EmailValidator.is_valid("   ") is False

    def test_invalid_email_none(self):
        """Should reject None."""
        assert EmailValidator.is_valid(None) is False

    def test_invalid_email_consecutive_dots(self):
        """Should reject email with consecutive dots."""
        assert EmailValidator.is_valid("user..name@example.com") is False

    def test_invalid_email_starts_with_dot(self):
        """Should reject email starting with dot."""
        assert EmailValidator.is_valid(".user@example.com") is False

    def test_invalid_email_ends_with_dot(self):
        """Should reject email ending with dot in local part."""
        assert EmailValidator.is_valid("user.@example.com") is False

    def test_invalid_email_domain_starts_with_dot(self):
        """Should reject domain starting with dot."""
        assert EmailValidator.is_valid("user@.example.com") is False

    def test_invalid_email_domain_label_starts_with_hyphen(self):
        """Should reject domain label starting with hyphen."""
        assert EmailValidator.is_valid("user@-example.com") is False

    def test_invalid_email_domain_label_ends_with_hyphen(self):
        """Should reject domain label ending with hyphen."""
        assert EmailValidator.is_valid("user@example-.com") is False

    def test_invalid_email_domain_ends_with_dot(self):
        """Should reject domain ending with dot."""
        assert EmailValidator.is_valid("user@example.com.") is False

    def test_invalid_email_spaces(self):
        """Should reject email with spaces."""
        assert EmailValidator.is_valid("user name@example.com") is False

    def test_invalid_email_special_chars(self):
        """Should reject email with invalid special characters."""
        assert EmailValidator.is_valid("user!name@example.com") is False

    def test_invalid_email_comma(self):
        """Should reject email with comma."""
        assert EmailValidator.is_valid("user,name@example.com") is False


class TestEmailValidatorValidate:
    """Test EmailValidator.validate() method."""

    def test_validate_valid_email(self):
        """Should not raise for valid email."""
        EmailValidator.validate("user@example.com")

    def test_validate_none_email(self):
        """Should not raise for None (optional field)."""
        EmailValidator.validate(None)

    def test_validate_invalid_email_raises_error(self):
        """Should raise ValueError for invalid email."""
        with pytest.raises(ValueError, match="Invalid email format"):
            EmailValidator.validate("invalid.email")

    def test_validate_empty_string_raises_error(self):
        """Should raise ValueError for empty string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            EmailValidator.validate("")

    def test_validate_whitespace_only_raises_error(self):
        """Should raise ValueError for whitespace only."""
        with pytest.raises(ValueError, match="cannot be empty"):
            EmailValidator.validate("   ")

    def test_validate_not_string_raises_error(self):
        """Should raise ValueError for non-string."""
        with pytest.raises(ValueError, match="must be a string"):
            EmailValidator.validate(123)

    def test_validate_too_long_email_raises_error(self):
        """Should raise ValueError for email longer than 254 characters."""
        long_email = "a" * 250 + "@example.com"
        with pytest.raises(ValueError, match="too long"):
            EmailValidator.validate(long_email)

    def test_validate_consecutive_dots_raises_error(self):
        """Should raise ValueError for consecutive dots."""
        with pytest.raises(ValueError, match="consecutive dots"):
            EmailValidator.validate("user..name@example.com")

    def test_validate_local_part_too_long_raises_error(self):
        """Should raise ValueError for local part longer than 64 characters."""
        long_local = "a" * 65 + "@example.com"
        with pytest.raises(ValueError, match="Local part"):
            EmailValidator.validate(long_local)

    def test_validate_local_part_empty_raises_error(self):
        """Should raise ValueError for empty local part."""
        with pytest.raises(ValueError, match="Local part cannot be empty"):
            EmailValidator.validate("@example.com")

    def test_validate_domain_starts_with_dot_raises_error(self):
        """Should raise ValueError for domain starting with dot."""
        with pytest.raises(ValueError, match="Domain cannot start"):
            EmailValidator.validate("user@.example.com")

    def test_validate_domain_ends_with_dot_raises_error(self):
        """Should raise ValueError for domain ending with dot."""
        with pytest.raises(ValueError, match="Domain cannot end"):
            EmailValidator.validate("user@example.com.")
            
class TestEmailValidationEdgeCases:
    """Test edge cases and special scenarios."""

    def test_email_with_hyphen_in_local_part(self):
        """Should accept email with hyphen in local part."""
        assert EmailValidator.is_valid("user-name@example.com") is True

    def test_email_numeric_only_local_part(self):
        """Should accept email with numeric-only local part."""
        assert EmailValidator.is_valid("12345@example.com") is True

    def test_email_numeric_only_domain(self):
        """Should reject numeric-only domain (no extension)."""
        assert EmailValidator.is_valid("user@12345") is False

    def test_email_with_hyphens_at_start_of_domain(self):
        """Should reject domain starting with hyphen."""
        assert EmailValidator.is_valid("user@-example.com") is False

    def test_email_with_hyphens_at_end_of_domain(self):
        """Should reject domain ending with hyphen."""
        assert EmailValidator.is_valid("user@example-.com") is False

    def test_email_single_character_local_part(self):
        """Should accept single character local part."""
        assert EmailValidator.is_valid("a@example.com") is True

    def test_email_two_letter_domain_extension(self):
        """Should accept two letter domain extension."""
        assert EmailValidator.is_valid("user@example.co") is True
