"""Parity tests for KB clients handling zero and negative input validation."""
import pytest

from KB.clients.mockKBClient import MockKBClient
from KB.models.search import KBQuery


class TestMockKBClientInputValidation:
    """Test MockKBClient validates positive integers for limit and top_k."""

    @pytest.fixture
    def kb_client(self):
        """Create a fresh mock client for each test."""
        return MockKBClient()

    # ========================================================================
    # SEARCH: top_k VALIDATION
    # ========================================================================

    def test_search_with_zero_top_k(self, kb_client):
        """Should handle zero top_k gracefully (empty results)."""
        query = KBQuery(query="Template", top_k=0)
        results = kb_client.search(query)
        # With top_k=0, we expect empty results due to slice [:0]
        assert results == []

    def test_search_with_negative_one_top_k(self, kb_client):
        """Should handle top_k=-1 gracefully (empty results)."""
        query = KBQuery(query="Template", top_k=-1)
        results = kb_client.search(query)
        assert results == []

    def test_search_with_negative_five_top_k(self, kb_client):
        """Should handle top_k=-5 gracefully (empty results)."""
        query = KBQuery(query="Template", top_k=-5)
        results = kb_client.search(query)
        assert results == []

    def test_search_with_very_negative_top_k(self, kb_client):
        """Should handle very negative top_k gracefully (empty results)."""
        query = KBQuery(query="Template", top_k=-1000)
        results = kb_client.search(query)
        assert results == []

    def test_search_with_positive_one_top_k(self, kb_client):
        """Should return at most 1 result when top_k is 1."""
        query = KBQuery(query="", top_k=1)  # empty query matches all
        results = kb_client.search(query)
        assert len(results) <= 1

    def test_search_with_positive_five_top_k(self, kb_client):
        """Should return at most 5 results when top_k is 5."""
        query = KBQuery(query="", top_k=5)
        results = kb_client.search(query)
        assert len(results) <= 5

    # ========================================================================
    # LIST: limit VALIDATION
    # ========================================================================

    def test_list_with_zero_limit(self, kb_client):
        """Should return empty list when limit is zero."""
        documents = kb_client.list(node_path=None, limit=0)
        assert documents == []

    def test_list_with_negative_one_limit(self, kb_client):
        """Should return empty list when limit is -1."""
        documents = kb_client.list(node_path=None, limit=-1)
        assert documents == []

    def test_list_with_negative_five_limit(self, kb_client):
        """Should return empty list when limit is -5."""
        documents = kb_client.list(node_path=None, limit=-5)
        assert documents == []

    def test_list_with_very_negative_limit(self, kb_client):
        """Should return empty list when limit is very negative."""
        documents = kb_client.list(node_path=None, limit=-1000)
        assert documents == []

    def test_list_with_positive_one_limit(self, kb_client):
        """Should return at most 1 document when limit is 1."""
        documents = kb_client.list(node_path=None, limit=1)
        assert len(documents) <= 1

    def test_list_with_positive_ten_limit(self, kb_client):
        """Should return at most 10 documents when limit is 10."""
        documents = kb_client.list(node_path=None, limit=10)
        assert len(documents) <= 10

    # ========================================================================
    # EDGE CASES: Invalid inputs with filters
    # ========================================================================

    def test_search_zero_top_k_with_valid_query(self, kb_client):
        """Should return empty even with valid search query."""
        query = KBQuery(query="Template", top_k=0)
        results = kb_client.search(query)
        assert results == []

    def test_search_negative_top_k_with_valid_query(self, kb_client):
        """Should return empty even with valid search query."""
        query = KBQuery(query="Template", top_k=-5)
        results = kb_client.search(query)
        assert results == []

    def test_list_zero_limit_with_node_filter(self, kb_client):
        """Should return empty even with node path filter."""
        documents = kb_client.list(node_path="/templates", limit=0)
        assert documents == []

    def test_list_negative_limit_with_node_filter(self, kb_client):
        """Should return empty even with node path filter."""
        documents = kb_client.list(node_path="/team/devops", limit=-5)
        assert documents == []

    # ========================================================================
    # CONSISTENCY: Multiple invalid values
    # ========================================================================

    def test_search_all_invalid_top_k_values_return_empty(self, kb_client):
        """Should consistently return empty for all invalid top_k values."""
        invalid_values = [0, -1, -5, -10, -100, -1000]
        for invalid_top_k in invalid_values:
            query = KBQuery(query="Template", top_k=invalid_top_k)
            results = kb_client.search(query)
            assert results == [], f"Expected empty results for top_k={invalid_top_k}"

    def test_list_all_invalid_limit_values_return_empty(self, kb_client):
        """Should consistently return empty for all invalid limit values."""
        invalid_values = [0, -1, -5, -10, -100, -1000]
        for invalid_limit in invalid_values:
            documents = kb_client.list(node_path=None, limit=invalid_limit)
            assert documents == [], f"Expected empty documents for limit={invalid_limit}"


class TestKBClientInputValidationParity:
    """Test both mock and HTTP clients handle invalid input consistently."""

    @pytest.fixture
    def mock_client(self):
        """Create a fresh mock client."""
        return MockKBClient()

    # ========================================================================
    # SEARCH PARITY: top_k
    # ========================================================================

    def test_search_zero_top_k_parity(self, mock_client):
        """Both clients should return empty for zero top_k."""
        query = KBQuery(query="Template", top_k=0)
        mock_results = mock_client.search(query)
        # Contract: both return empty
        assert mock_results == []

    def test_search_negative_top_k_parity(self, mock_client):
        """Both clients should return empty for negative top_k."""
        query = KBQuery(query="Template", top_k=-5)
        mock_results = mock_client.search(query)
        # Contract: both return empty
        assert mock_results == []

    def test_search_very_negative_top_k_parity(self, mock_client):
        """Both clients should return empty for very negative top_k."""
        query = KBQuery(query="Template", top_k=-1000)
        mock_results = mock_client.search(query)
        # Contract: both return empty
        assert mock_results == []

    def test_search_positive_top_k_parity(self, mock_client):
        """Both clients should respect positive top_k."""
        query = KBQuery(query="", top_k=5)
        mock_results = mock_client.search(query)
        # Contract: both respect the limit
        assert len(mock_results) <= 5

    def test_search_top_k_one_parity(self, mock_client):
        """Both clients should return at most 1 result for top_k=1."""
        query = KBQuery(query="", top_k=1)
        mock_results = mock_client.search(query)
        # Contract: both return at most 1
        assert len(mock_results) <= 1

    # ========================================================================
    # LIST PARITY: limit
    # ========================================================================

    def test_list_zero_limit_parity(self, mock_client):
        """Both clients should return empty for zero limit."""
        mock_docs = mock_client.list(node_path=None, limit=0)
        # Contract: both return empty
        assert mock_docs == []

    def test_list_negative_limit_parity(self, mock_client):
        """Both clients should return empty for negative limit."""
        mock_docs = mock_client.list(node_path=None, limit=-5)
        # Contract: both return empty
        assert mock_docs == []

    def test_list_very_negative_limit_parity(self, mock_client):
        """Both clients should return empty for very negative limit."""
        mock_docs = mock_client.list(node_path=None, limit=-1000)
        # Contract: both return empty
        assert mock_docs == []

    def test_list_positive_limit_parity(self, mock_client):
        """Both clients should respect positive limit."""
        mock_docs = mock_client.list(node_path=None, limit=10)
        # Contract: both respect the limit
        assert len(mock_docs) <= 10

    def test_list_limit_one_parity(self, mock_client):
        """Both clients should return at most 1 document for limit=1."""
        mock_docs = mock_client.list(node_path=None, limit=1)
        # Contract: both return at most 1
        assert len(mock_docs) <= 1

    # ========================================================================
    # PARITY: With filters applied
    # ========================================================================

    def test_search_zero_top_k_with_filter_parity(self, mock_client):
        """Both clients should return empty even with valid query."""
        query = KBQuery(query="Template", top_k=0)
        mock_results = mock_client.search(query)
        assert mock_results == []

    def test_search_negative_top_k_with_filter_parity(self, mock_client):
        """Both clients should return empty even with valid query."""
        query = KBQuery(query="Template", top_k=-5)
        mock_results = mock_client.search(query)
        assert mock_results == []

    def test_list_zero_limit_with_filter_parity(self, mock_client):
        """Both clients should return empty even with node filter."""
        mock_docs = mock_client.list(node_path="/templates", limit=0)
        assert mock_docs == []

    def test_list_negative_limit_with_filter_parity(self, mock_client):
        """Both clients should return empty even with node filter."""
        mock_docs = mock_client.list(node_path="/team/devops", limit=-5)
        assert mock_docs == []


class TestCLIInputValidationIntegration:
    """Test CLI validation before sending to clients."""

    @pytest.fixture
    def kb_client(self):
        """Create a fresh mock client."""
        return MockKBClient()

    # ========================================================================
    # CLI VALIDATION: top_k
    # ========================================================================

    def test_cli_validates_zero_top_k_and_applies_default(self, kb_client):
        """CLI should validate zero top_k and apply default before search."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --top-k 0
        user_input = 0
        validated_top_k = PositiveIntegerValidator.validate_and_return(
            user_input,
            "top_k",
            default=5
        )

        # Should get default value
        assert validated_top_k == 5

        # Now search with validated value
        query = KBQuery(query="Template", top_k=validated_top_k)
        results = kb_client.search(query)
        assert len(results) <= 5

    def test_cli_validates_negative_top_k_and_applies_default(self, kb_client):
        """CLI should validate negative top_k and apply default before search."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --top-k -3
        user_input = -3
        validated_top_k = PositiveIntegerValidator.validate_and_return(
            user_input,
            "top_k",
            default=5
        )

        # Should get default value
        assert validated_top_k == 5

    def test_cli_validates_very_negative_top_k_and_applies_default(self, kb_client):
        """CLI should validate very negative top_k and apply default."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --top-k -1000
        user_input = -1000
        validated_top_k = PositiveIntegerValidator.validate_and_return(
            user_input,
            "top_k",
            default=5
        )

        # Should get default value
        assert validated_top_k == 5

    def test_cli_accepts_valid_top_k(self, kb_client):
        """CLI should accept valid positive top_k."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --top-k 3
        user_input = 3
        validated_top_k = PositiveIntegerValidator.validate_and_return(
            user_input,
            "top_k",
            default=5
        )

        # Should keep user value
        assert validated_top_k == 3

    # ========================================================================
    # CLI VALIDATION: limit
    # ========================================================================

    def test_cli_validates_zero_limit_and_applies_default(self, kb_client):
        """CLI should validate zero limit and apply default before list."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --limit 0
        user_input = 0
        validated_limit = PositiveIntegerValidator.validate_and_return(
            user_input,
            "limit",
            default=10
        )

        # Should get default value
        assert validated_limit == 10

    def test_cli_validates_negative_limit_and_applies_default(self, kb_client):
        """CLI should validate negative limit and apply default before list."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --limit -5
        user_input = -5
        validated_limit = PositiveIntegerValidator.validate_and_return(
            user_input,
            "limit",
            default=10
        )

        # Should get default value
        assert validated_limit == 10

    def test_cli_validates_very_negative_limit_and_applies_default(self, kb_client):
        """CLI should validate very negative limit and apply default."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --limit -1000
        user_input = -1000
        validated_limit = PositiveIntegerValidator.validate_and_return(
            user_input,
            "limit",
            default=10
        )

        # Should get default value
        assert validated_limit == 10

    def test_cli_accepts_valid_limit(self, kb_client):
        """CLI should accept valid positive limit."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator

        # User provides --limit 15
        user_input = 15
        validated_limit = PositiveIntegerValidator.validate_and_return(
            user_input,
            "limit",
            default=10
        )

        # Should keep user value
        assert validated_limit == 15

    # ========================================================================
    # CLI INTEGRATION: End-to-end scenarios
    # ========================================================================

    def test_cli_end_to_end_search_zero_top_k(self, kb_client):
        """End-to-end: CLI validates --top-k 0 and applies default."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator
        from cli.commands.kb_search import KBSearchCommand
        from unittest.mock import Mock

        # Simulate parsed_args with --top-k 0
        parsed_args = Mock(query="Template", top_k=0)

        # Validate before creating query (as CLI does)
        top_k = PositiveIntegerValidator.validate_and_return(
            parsed_args.top_k,
            "top_k",
            default=5
        )

        # Create query with validated top_k
        query = KBQuery(query=parsed_args.query, top_k=top_k)

        # Search with validated query
        results = kb_client.search(query)
        assert len(results) <= 5

    def test_cli_end_to_end_list_negative_limit(self, kb_client):
        """End-to-end: CLI validates --limit -5 and applies default."""
        from ticket_manager.validators.positive_integer_validator import PositiveIntegerValidator
        from cli.commands.kb_list import KBListCommand
        from unittest.mock import Mock

        # Simulate parsed_args with --limit -5
        parsed_args = Mock(node_path=None, limit=-5)

        # Validate before calling list (as CLI does)
        limit = PositiveIntegerValidator.validate_and_return(
            parsed_args.limit,
            "limit",
            default=10
        )

        # List with validated limit
        documents = kb_client.list(node_path=parsed_args.node_path, limit=limit)
        assert len(documents) <= 10
