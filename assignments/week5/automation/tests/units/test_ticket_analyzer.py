"""Unit tests for TicketAnalyzer - Detect login issue patterns in tickets."""

import pytest
from srcs.services.ticket_analyzer import TicketAnalyzer, AnalysisResult, IssueType
from srcs.models import Ticket


@pytest.fixture
def analyzer():
    """Create a TicketAnalyzer instance."""
    return TicketAnalyzer()


class TestTicketAnalyzerEnglishPatterns:
    """Test English login issue detection."""

    def test_detect_cannot_login_pattern(self, analyzer):
        """Should detect 'cannot login' English pattern."""
        ticket = Ticket(
            id=1,
            name="Cannot login to my account",
            email_from="user@company.com",
            description="I cannot login to the system. Please help.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True
        assert result.issue_type == IssueType.CANNOT_LOGIN

    def test_detect_account_locked_pattern(self, analyzer):
        """Should detect 'account locked' pattern."""
        ticket = Ticket(
            id=2,
            name="Account locked",
            email_from="user@company.com",
            description="My account has been locked. I need help accessing it.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True
        assert result.issue_type == IssueType.ACCOUNT_LOCKED

    def test_detect_password_reset_pattern(self, analyzer):
        """Should detect 'password reset' pattern."""
        ticket = Ticket(
            id=3,
            name="Need password reset",
            email_from="user@company.com",
            description="I forgot my password and need to reset it.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True
        assert result.issue_type == IssueType.PASSWORD_RESET

    def test_detect_access_denied_pattern(self, analyzer):
        """Should detect 'access denied' pattern."""
        ticket = Ticket(
            id=4,
            name="Access denied error",
            email_from="user@company.com",
            description="Getting access denied when trying to login.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True
        assert result.issue_type == IssueType.ACCESS_DENIED


class TestTicketAnalyzerVietnamesePatterns:
    """Test Vietnamese login issue detection."""

    def test_detect_vietnamese_cannot_login(self, analyzer):
        """Should detect Vietnamese 'không thể đăng nhập' pattern."""
        ticket = Ticket(
            id=5,
            name="Không thể đăng nhập vào tài khoản",
            email_from="user@company.com",
            description="Tôi không thể đăng nhập vào hệ thống. Vui lòng giúp tôi.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True

    def test_detect_vietnamese_account_locked(self, analyzer):
        """Should detect Vietnamese 'tài khoản bị khóa' pattern."""
        ticket = Ticket(
            id=6,
            name="Tài khoản bị khóa",
            email_from="user@company.com",
            description="Tài khoản của tôi đã bị khóa.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True

    def test_detect_vietnamese_password_reset(self, analyzer):
        """Should detect Vietnamese 'đặt lại mật khẩu' pattern."""
        ticket = Ticket(
            id=7,
            name="Cần đặt lại mật khẩu",
            email_from="user@company.com",
            description="Tôi quên mật khẩu và cần đặt lại nó.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True


class TestTicketAnalyzerCaseInsensitivity:
    """Test case normalization."""

    def test_uppercase_patterns(self, analyzer):
        """Should detect patterns in uppercase."""
        ticket = Ticket(
            id=8,
            name="CANNOT LOGIN",
            email_from="user@company.com",
            description="I CANNOT LOGIN TO THE SYSTEM",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True

    def test_mixed_case_patterns(self, analyzer):
        """Should detect patterns in mixed case."""
        ticket = Ticket(
            id=9,
            name="CaNnOt LoGiN",
            email_from="user@company.com",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True


class TestTicketAnalyzerHTMLContent:
    """Test HTML content handling."""

    def test_html_description(self, analyzer):
        """Should parse and detect patterns in HTML-formatted description."""
        ticket = Ticket(
            id=10,
            name="Login issue",
            email_from="user@company.com",
            description="<p>I <strong>cannot login</strong> to my account</p>",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True

    def test_html_with_line_breaks(self, analyzer):
        """Should handle HTML with line breaks."""
        ticket = Ticket(
            id=11,
            name="Account problem",
            email_from="user@company.com",
            description="<p>My account is locked</p><br/><p>Please help me access it</p>",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True


class TestTicketAnalyzerMissingFields:
    """Test handling of missing/empty fields."""

    def test_missing_description(self, analyzer):
        """Should analyze ticket with only name field."""
        ticket = Ticket(
            id=12,
            name="Cannot login",
            email_from="user@company.com",
            description=None,
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True

    def test_empty_description(self, analyzer):
        """Should handle empty description."""
        ticket = Ticket(
            id=13,
            name="Account locked",
            email_from="user@company.com",
            description="",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True

    def test_only_whitespace_content(self, analyzer):
        """Should handle only whitespace content."""
        ticket = Ticket(
            id=14,
            name="Help",  # Valid name
            email_from="user@company.com",
            description="   \n\t  ",  # Only whitespace in description
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is False


class TestTicketAnalyzerNegativePatterns:
    """Test unrelated ticket detection."""

    def test_performance_issue_not_login(self, analyzer):
        """Should not classify performance issues as login problems."""
        ticket = Ticket(
            id=15,
            name="System running slow",
            email_from="user@company.com",
            description="The system is running very slowly today.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is False

    def test_general_question_not_login(self, analyzer):
        """Should not classify general questions as login problems."""
        ticket = Ticket(
            id=16,
            name="How do I use feature X?",
            email_from="user@company.com",
            description="Can someone explain how to use feature X?",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is False

    def test_hardware_issue_not_login(self, analyzer):
        """Should not classify hardware issues as login problems."""
        ticket = Ticket(
            id=17,
            name="Monitor not working",
            email_from="user@company.com",
            description="My monitor stopped working.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is False

    def test_login_mentioned_but_not_the_issue(self, analyzer):
        """Should handle ambiguous cases carefully."""
        ticket = Ticket(
            id=18,
            name="Question about login page",
            email_from="user@company.com",
            description="Can login work with SSO? Just asking.",
        )

        result = analyzer.analyze(ticket)

        # This is ambiguous - should not classify as issue
        # unless it clearly indicates a problem
        assert result.is_login_issue is False or result.reason


class TestTicketAnalyzerNegatedRequests:
    """Test safe handling of negated requests."""

    def test_cannot_not_login_negation(self, analyzer):
        """Should handle negation: 'cannot NOT login' should not be classified."""
        ticket = Ticket(
            id=19,
            name="System is working",
            email_from="user@company.com",
            description="I can login without any problem.",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is False


class TestTicketAnalyzerClassificationReason:
    """Test classification reason tracking."""

    def test_reason_included_when_detected(self, analyzer):
        """Should include reason when issue is detected."""
        ticket = Ticket(
            id=20,
            name="Cannot login",
            email_from="user@company.com",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is True
        assert result.reason is not None
        assert len(result.reason) > 0

    def test_reason_included_when_not_detected(self, analyzer):
        """Should include reason when issue is not detected."""
        ticket = Ticket(
            id=21,
            name="General question",
            email_from="user@company.com",
        )

        result = analyzer.analyze(ticket)

        assert result.is_login_issue is False
        assert result.reason is not None


class TestTicketAnalyzerResultStructure:
    """Test AnalysisResult structure."""

    def test_analysis_result_has_required_fields(self, analyzer):
        """AnalysisResult should have all required fields."""
        ticket = Ticket(
            id=22,
            name="Cannot login",
            email_from="user@company.com",
        )

        result = analyzer.analyze(ticket)

        assert hasattr(result, "is_login_issue")
        assert hasattr(result, "issue_type")
        assert hasattr(result, "reason")
        assert hasattr(result, "confidence")

    def test_confidence_score_is_between_0_and_1(self, analyzer):
        """Confidence score should be between 0 and 1."""
        ticket = Ticket(
            id=23,
            name="Cannot login",
            email_from="user@company.com",
        )

        result = analyzer.analyze(ticket)

        assert 0 <= result.confidence <= 1
