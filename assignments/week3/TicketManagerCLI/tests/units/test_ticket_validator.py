import pytest
from ticket_manager.validators import TicketValidator


class TestTicketValidatorTitle:
    """Test TicketValidator.validate_title() method."""

    def test_validate_title_valid(self):
        """Should not raise for valid title."""
        TicketValidator.validate_title("Fix login bug")

    def test_validate_title_minimum_length(self):
        """Should accept title with minimum 3 characters."""
        TicketValidator.validate_title("Fix")

    def test_validate_title_too_short(self):
        """Should raise ValueError for title shorter than 3 characters."""
        with pytest.raises(ValueError, match="too short"):
            TicketValidator.validate_title("ab")

    def test_validate_title_too_long(self):
        """Should raise ValueError for title longer than 255 characters."""
        long_title = "a" * 256
        with pytest.raises(ValueError, match="too long"):
            TicketValidator.validate_title(long_title)

    def test_validate_title_empty_raises_error(self):
        """Should raise ValueError for empty title."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TicketValidator.validate_title("")

    def test_validate_title_whitespace_only_raises_error(self):
        """Should raise ValueError for whitespace only."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TicketValidator.validate_title("   ")

    def test_validate_title_not_string_raises_error(self):
        """Should raise ValueError for non-string."""
        with pytest.raises(ValueError, match="must be a string"):
            TicketValidator.validate_title(123)


class TestTicketValidatorDescription:
    """Test TicketValidator.validate_description() method."""

    def test_validate_description_valid(self):
        """Should not raise for valid description."""
        TicketValidator.validate_description("This is a valid description")

    def test_validate_description_empty(self):
        """Should accept empty description."""
        TicketValidator.validate_description("")

    def test_validate_description_too_long(self):
        """Should raise ValueError for description longer than 5000 characters."""
        long_desc = "a" * 5001
        with pytest.raises(ValueError, match="too long"):
            TicketValidator.validate_description(long_desc)

    def test_validate_description_not_string_raises_error(self):
        """Should raise ValueError for non-string."""
        with pytest.raises(ValueError, match="must be a string"):
            TicketValidator.validate_description(123)


class TestTicketValidatorPriority:
    """Test TicketValidator.validate_priority() method."""

    def test_validate_priority_low(self):
        """Should accept low priority."""
        TicketValidator.validate_priority("low")

    def test_validate_priority_medium(self):
        """Should accept medium priority."""
        TicketValidator.validate_priority("medium")

    def test_validate_priority_high(self):
        """Should accept high priority."""
        TicketValidator.validate_priority("high")

    def test_validate_priority_invalid(self):
        """Should raise ValueError for invalid priority."""
        with pytest.raises(ValueError, match="Invalid priority"):
            TicketValidator.validate_priority("critical")

    def test_validate_priority_empty_raises_error(self):
        """Should raise ValueError for empty string."""
        with pytest.raises(ValueError, match="Invalid priority"):
            TicketValidator.validate_priority("")

    def test_validate_priority_mixed_case_raises_error(self):
        """Should raise ValueError for mixed case."""
        with pytest.raises(ValueError, match="Invalid priority"):
            TicketValidator.validate_priority("High")


class TestTicketValidatorStatus:
    """Test TicketValidator.validate_status() method."""

    def test_validate_status_open(self):
        """Should accept open status."""
        TicketValidator.validate_status("open")

    def test_validate_status_in_progress(self):
        """Should accept in-progress status."""
        TicketValidator.validate_status("in-progress")

    def test_validate_status_closed(self):
        """Should accept closed status."""
        TicketValidator.validate_status("closed")

    def test_validate_status_invalid(self):
        """Should raise ValueError for invalid status."""
        with pytest.raises(ValueError, match="Invalid status"):
            TicketValidator.validate_status("done")

    def test_validate_status_empty_raises_error(self):
        """Should raise ValueError for empty string."""
        with pytest.raises(ValueError, match="Invalid status"):
            TicketValidator.validate_status("")


class TestTicketValidatorTags:
    """Test TicketValidator.validate_tags() method."""

    def test_validate_tags_empty_list(self):
        """Should accept empty tag list."""
        TicketValidator.validate_tags([])

    def test_validate_tags_single_tag(self):
        """Should accept single tag."""
        TicketValidator.validate_tags(["bug"])

    def test_validate_tags_multiple_tags(self):
        """Should accept multiple tags."""
        TicketValidator.validate_tags(["bug", "frontend", "urgent"])

    def test_validate_tags_maximum_tags(self):
        """Should accept maximum 10 tags."""
        TicketValidator.validate_tags(["tag" + str(i) for i in range(10)])

    def test_validate_tags_too_many_raises_error(self):
        """Should raise ValueError for more than 10 tags."""
        with pytest.raises(ValueError, match="Too many tags"):
            TicketValidator.validate_tags(["tag" + str(i) for i in range(11)])

    def test_validate_tags_not_list_raises_error(self):
        """Should raise ValueError for non-list."""
        with pytest.raises(ValueError, match="must be a list"):
            TicketValidator.validate_tags("bug,frontend")

    def test_validate_tags_non_string_tag_raises_error(self):
        """Should raise ValueError for non-string tag."""
        with pytest.raises(ValueError, match="must be a string"):
            TicketValidator.validate_tags(["bug", 123])

    def test_validate_tags_empty_tag_raises_error(self):
        """Should raise ValueError for empty tag."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TicketValidator.validate_tags(["bug", ""])

    def test_validate_tags_whitespace_tag_raises_error(self):
        """Should raise ValueError for whitespace only tag."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TicketValidator.validate_tags(["bug", "   "])

    def test_validate_tags_too_short_raises_error(self):
        """Should raise ValueError for tag shorter than 2 characters."""
        with pytest.raises(ValueError, match="too short"):
            TicketValidator.validate_tags(["a"])

    def test_validate_tags_too_long_raises_error(self):
        """Should raise ValueError for tag longer than 50 characters."""
        long_tag = "a" * 51
        with pytest.raises(ValueError, match="too long"):
            TicketValidator.validate_tags([long_tag])


class TestTicketValidatorCreator:
    """Test TicketValidator.validate_creator() method."""

    def test_validate_creator_valid_email(self):
        """Should not raise for valid creator email."""
        TicketValidator.validate_creator("creator@example.com")

    def test_validate_creator_none(self):
        """Should not raise for None creator."""
        TicketValidator.validate_creator(None)

    def test_validate_creator_invalid_email_raises_error(self):
        """Should raise ValueError for invalid creator email."""
        with pytest.raises(ValueError):
            TicketValidator.validate_creator("invalid.email")

    def test_validate_creator_empty_string_raises_error(self):
        """Should raise ValueError for empty creator email."""
        with pytest.raises(ValueError):
            TicketValidator.validate_creator("")


class TestTicketValidatorAssignee:
    """Test TicketValidator.validate_assignee() method."""

    def test_validate_assignee_valid_email(self):
        """Should not raise for valid assignee email."""
        TicketValidator.validate_assignee("assignee@example.com")

    def test_validate_assignee_none(self):
        """Should not raise for None assignee."""
        TicketValidator.validate_assignee(None)

    def test_validate_assignee_invalid_email_raises_error(self):
        """Should raise ValueError for invalid assignee email."""
        with pytest.raises(ValueError):
            TicketValidator.validate_assignee("invalid.email")

    def test_validate_assignee_empty_string_raises_error(self):
        """Should raise ValueError for empty assignee email."""
        with pytest.raises(ValueError):
            TicketValidator.validate_assignee("")


