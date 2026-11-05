"""Ticket analyzer service - Detect login issue patterns in tickets."""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from html.parser import HTMLParser

from srcs.models import Ticket

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Types of login issues that can be detected."""

    CANNOT_LOGIN = "cannot_login"
    ACCOUNT_LOCKED = "account_locked"
    PASSWORD_RESET = "password_reset"
    ACCESS_DENIED = "access_denied"
    INACTIVE_ACCOUNT = "inactive_account"
    UNKNOWN = "unknown"


@dataclass
class AnalysisResult:
    """Result of ticket analysis."""

    is_login_issue: bool
    issue_type: Optional[IssueType] = None
    reason: str = ""
    confidence: float = 0.0  # 0.0 to 1.0


class HTMLStripper(HTMLParser):
    """Extract text from HTML content, preserving spaces between tags."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, data):
        """Collect text data."""
        self.fed.append(data)

    def handle_starttag(self, tag, attrs):
        """Add space before opening tag if needed."""
        # Add space before block-level tags to preserve word boundaries
        if tag in ["p", "div", "br", "blockquote", "li"]:
            if self.fed and self.fed[-1] and not self.fed[-1].endswith(" "):
                self.fed.append(" ")

    def handle_endtag(self, tag):
        """Add space after closing tag if needed."""
        # Add space after block-level tags
        if tag in ["p", "div", "blockquote", "li"]:
            if self.fed and self.fed[-1] and not self.fed[-1].endswith(" "):
                self.fed.append(" ")

    def get_text(self):
        """Get collected text."""
        return "".join(self.fed)


class TicketAnalyzer:
    """Analyze tickets to identify login issue patterns.

    Supports:
    - English and Vietnamese keywords
    - Case-insensitive matching
    - HTML content parsing
    - Multiple issue types classification
    """

    # English patterns for different issue types
    ENGLISH_CANNOT_LOGIN = [
        r"\bcannot\s+login\b",
        r"\bcan't\s+login\b",
        r"\bcannot\s+log\s+in\b",
        r"\bcan't\s+log\s+in\b",
        r"\bunable\s+to\s+login\b",
        r"\bunable\s+to\s+log\s+in\b",
        r"\bcannot\s+access\b",
        r"\bcan't\s+access\b",
    ]

    ENGLISH_ACCOUNT_LOCKED = [
        r"\baccount\s+locked\b",
        r"\baccount\s+is\s+locked\b",
        r"\bmy\s+account\s+locked\b",
        r"\buser\s+locked\b",
    ]

    ENGLISH_PASSWORD_RESET = [
        r"\bpassword\s+reset\b",
        r"\breset\s+password\b",
        r"\bforgot\s+password\b",
        r"\bforgot\s+my\s+password\b",
        r"\bneed.*password\b",
    ]

    ENGLISH_ACCESS_DENIED = [
        r"\baccess\s+denied\b",
        r"\bdenied\s+access\b",
        r"\bunauthorized\b",
        r"\bpermission\s+denied\b",
    ]

    # Vietnamese patterns
    VIETNAMESE_CANNOT_LOGIN = [
        r"\bkhông\s+thể\s+đăng\s+nhập\b",
        r"\bkhông\s+đăng\s+nhập\s+được\b",
        r"\bkhông\s+thể\s+truy\s+cập\b",
    ]

    VIETNAMESE_ACCOUNT_LOCKED = [
        r"\btài\s+khoản\s+bị\s+khóa\b",
        r"\bkhóa\s+tài\s+khoản\b",
    ]

    VIETNAMESE_PASSWORD_RESET = [
        r"\bđặt\s+lại\s+mật\s+khẩu\b",
        r"\bquên\s+mật\s+khẩu\b",
    ]

    def analyze(self, ticket: Ticket) -> AnalysisResult:
        """Analyze a ticket to detect login issues.

        Args:
            ticket: Ticket model to analyze

        Returns:
            AnalysisResult with classification and confidence
        """
        try:
            # Combine content for analysis
            content = self._extract_content(ticket)

            if not content or not content.strip():
                return AnalysisResult(
                    is_login_issue=False,
                    reason="Ticket has no content to analyze",
                    confidence=0.0,
                )

            # Check for negation patterns (e.g., "I can login without any problem")
            if self._is_negated(content):
                return AnalysisResult(
                    is_login_issue=False,
                    reason="Ticket content is negated",
                    confidence=0.95,
                )

            # Normalize content for matching
            normalized = self._normalize_content(content)

            # Check each issue type
            result = self._check_issue_types(normalized, content)

            if result.is_login_issue:
                result.confidence = 0.9  # High confidence for detected patterns
            else:
                result.confidence = 0.85  # High confidence for non-issue classification

            return result

        except Exception as e:
            logger.error(f"Error analyzing ticket {ticket.id}: {str(e)}")
            return AnalysisResult(
                is_login_issue=False,
                reason=f"Error during analysis: {str(e)}",
                confidence=0.0,
            )

    def _extract_content(self, ticket: Ticket) -> str:
        """Extract text content from ticket, handling HTML."""
        parts = []

        # Add ticket name if present
        if ticket.name:
            parts.append(ticket.name)

        # Add description if present, stripping HTML
        if ticket.description:
            description_text = self._strip_html(ticket.description)
            parts.append(description_text)

        return " ".join(parts)

    def _strip_html(self, html_content: str) -> str:
        """Remove HTML tags from content."""
        try:
            stripper = HTMLStripper()
            stripper.feed(html_content)
            return stripper.get_text()
        except Exception as e:
            logger.warning(f"Error stripping HTML: {str(e)}")
            # Fallback: remove obvious HTML tags
            text = re.sub(r"<[^>]+>", " ", html_content)
            return text

    def _normalize_content(self, content: str) -> str:
        """Normalize content for pattern matching."""
        # Convert to lowercase for case-insensitive matching
        normalized = content.lower()
        # Replace common Unicode variations
        normalized = normalized.replace("\\u0000", "")
        return normalized

    def _is_negated(self, content: str) -> bool:
        """Check if the issue description is negated."""
        normalized = self._normalize_content(content)

        # Patterns indicating negation (positive statement, not a problem)
        negation_patterns = [
            r"\bcan\s+login\b",
            r"\bcan\s+access\b",
            r"\bworking\s+fine\b",
            r"\bno\s+problem\b",
            r"\bworking\s+correctly\b",
            r"\bno\s+issue\b",
        ]

        for pattern in negation_patterns:
            if re.search(pattern, normalized):
                return True

        return False

    def _check_issue_types(
        self, normalized_content: str, original_content: str
    ) -> AnalysisResult:
        """Check for specific issue types."""

        # Check cannot login
        if self._match_patterns(
            normalized_content,
            self.ENGLISH_CANNOT_LOGIN + self.VIETNAMESE_CANNOT_LOGIN,
        ):
            return AnalysisResult(
                is_login_issue=True,
                issue_type=IssueType.CANNOT_LOGIN,
                reason="Detected 'cannot login' pattern",
            )

        # Check account locked
        if self._match_patterns(
            normalized_content,
            self.ENGLISH_ACCOUNT_LOCKED + self.VIETNAMESE_ACCOUNT_LOCKED,
        ):
            return AnalysisResult(
                is_login_issue=True,
                issue_type=IssueType.ACCOUNT_LOCKED,
                reason="Detected 'account locked' pattern",
            )

        # Check password reset
        if self._match_patterns(
            normalized_content,
            self.ENGLISH_PASSWORD_RESET + self.VIETNAMESE_PASSWORD_RESET,
        ):
            return AnalysisResult(
                is_login_issue=True,
                issue_type=IssueType.PASSWORD_RESET,
                reason="Detected 'password reset' pattern",
            )

        # Check access denied
        if self._match_patterns(
            normalized_content, self.ENGLISH_ACCESS_DENIED
        ):
            return AnalysisResult(
                is_login_issue=True,
                issue_type=IssueType.ACCESS_DENIED,
                reason="Detected 'access denied' pattern",
            )

        # No login issue detected
        return AnalysisResult(
            is_login_issue=False,
            issue_type=IssueType.UNKNOWN,
            reason="No login issue pattern detected",
        )

    def _match_patterns(self, content: str, patterns: list) -> bool:
        """Check if any pattern matches the content."""
        for pattern in patterns:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            except re.error as e:
                logger.warning(f"Invalid regex pattern {pattern}: {str(e)}")
                continue

        return False
