"""Unit tests for TicketFingerprinter."""

import pytest
from srcs.models import Ticket
from srcs.services.ticket_fingerprinter import TicketFingerprinter


class TestTicketFingerprinterGeneration:
    """Test fingerprint generation."""

    def test_generate_valid_ticket(self):
        """Should generate fingerprint for valid ticket."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fingerprint = TicketFingerprinter.generate(ticket)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA-256 hex is 64 chars
        assert all(c in '0123456789abcdef' for c in fingerprint)

    def test_generate_same_content_same_fingerprint(self):
        """Should generate same fingerprint for identical content."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I can't access my account",
        )

        ticket2 = Ticket(
            id=2,
            name="Cannot login",
            email_from="user@company.com",
            description="I can't access my account",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Different ticket IDs but same content = same fingerprint
        assert fp1 == fp2

    def test_generate_different_content_different_fingerprint(self):
        """Should generate different fingerprints for different content."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="other@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        assert fp1 != fp2

    def test_generate_normalizes_whitespace(self):
        """Should normalize whitespace in fingerprint."""
        ticket1 = Ticket(
            id=1,
            name="Cannot   login",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Extra whitespace should be normalized
        assert fp1 == fp2

    def test_generate_normalizes_case(self):
        """Should normalize case in fingerprint."""
        ticket1 = Ticket(
            id=1,
            name="CANNOT LOGIN",
            email_from="USER@COMPANY.COM",
        )

        ticket2 = Ticket(
            id=1,
            name="cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Case should be normalized
        assert fp1 == fp2

    def test_generate_handles_none_values(self):
        """Should handle None values in fields."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description=None,
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # None and empty string should be treated same
        assert fp1 == fp2

    def test_generate_ignores_ticket_id(self):
        """Should ignore ticket ID in fingerprint."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=999,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Ticket ID shouldn't affect fingerprint
        assert fp1 == fp2

    def test_generate_includes_name(self):
        """Should include ticket name in fingerprint."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Password expired",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Different names should produce different fingerprints
        assert fp1 != fp2

    def test_generate_includes_description(self):
        """Should include description in fingerprint."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I've been locked out",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I forgot my password",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Different descriptions should produce different fingerprints
        assert fp1 != fp2

    def test_generate_includes_email_from(self):
        """Should include email_from in fingerprint."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="alice@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="bob@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Different email_from should produce different fingerprints
        assert fp1 != fp2

    def test_generate_with_all_fields(self):
        """Should include all relevant fields in fingerprint."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I can't access",
            stage_id=1,
            tags=["login_issues", "urgent"],
        )

        fingerprint = TicketFingerprinter.generate(ticket)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64

    def test_generate_none_ticket_raises(self):
        """Should raise ValueError for None ticket."""
        with pytest.raises(ValueError):
            TicketFingerprinter.generate(None)


class TestTicketFingerprinterComparison:
    """Test fingerprint comparison for change detection."""

    def test_has_changed_content_unchanged(self):
        """Should return False when content unchanged."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket)
        changed = TicketFingerprinter.has_changed(ticket, fp1)

        assert changed is False

    def test_has_changed_name_modified(self):
        """Should return True when name changed."""
        ticket_original = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp_original = TicketFingerprinter.generate(ticket_original)

        # Ticket name changed
        ticket_modified = Ticket(
            id=1,
            name="Cannot login - urgent",
            email_from="user@company.com",
        )

        changed = TicketFingerprinter.has_changed(ticket_modified, fp_original)

        assert changed is True

    def test_has_changed_description_modified(self):
        """Should return True when description changed."""
        ticket_original = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I'm locked out",
        )

        fp_original = TicketFingerprinter.generate(ticket_original)

        # Description updated with more details
        ticket_modified = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I'm locked out and need urgent help",
        )

        changed = TicketFingerprinter.has_changed(ticket_modified, fp_original)

        assert changed is True

    def test_has_changed_email_modified(self):
        """Should return True when email changed."""
        ticket_original = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp_original = TicketFingerprinter.generate(ticket_original)

        # Email changed (e.g., corrected by support)
        ticket_modified = Ticket(
            id=1,
            name="Cannot login",
            email_from="user.correct@company.com",
        )

        changed = TicketFingerprinter.has_changed(ticket_modified, fp_original)

        assert changed is True

    def test_has_changed_none_previous_fingerprint(self):
        """Should return True when no previous fingerprint."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        changed = TicketFingerprinter.has_changed(ticket, None)

        assert changed is True

    def test_has_changed_empty_previous_fingerprint(self):
        """Should return True when previous fingerprint is empty."""
        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        changed = TicketFingerprinter.has_changed(ticket, "")

        assert changed is True

    def test_has_changed_ignores_ticket_id_change(self):
        """Should not detect change if only ticket ID differs."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)

        # Same content, different ID (shouldn't happen, but test anyway)
        ticket2 = Ticket(
            id=2,
            name="Cannot login",
            email_from="user@company.com",
        )

        changed = TicketFingerprinter.has_changed(ticket2, fp1)

        # Should not detect as changed
        assert changed is False


class TestTicketFingerprinterNormalization:
    """Test content normalization."""

    def test_normalize_handles_leading_trailing_spaces(self):
        """Should strip leading/trailing spaces."""
        ticket1 = Ticket(
            id=1,
            name="  Cannot login  ",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        assert fp1 == fp2

    def test_normalize_handles_tabs_and_newlines(self):
        """Should normalize tabs and newlines to spaces."""
        ticket1 = Ticket(
            id=1,
            name="Cannot\tlogin",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        assert fp1 == fp2

    def test_normalize_handles_multiple_spaces(self):
        """Should collapse multiple spaces to single space."""
        ticket1 = Ticket(
            id=1,
            name="Cannot     login     here",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="Cannot login here",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        assert fp1 == fp2

    def test_normalize_consistent_with_unicode(self):
        """Should handle unicode consistently."""
        ticket1 = Ticket(
            id=1,
            name="Cannot login café",
            email_from="user@company.com",
        )

        ticket2 = Ticket(
            id=1,
            name="CANNOT LOGIN CAFÉ",
            email_from="user@company.com",
        )

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Unicode should be normalized consistently
        assert fp1 == fp2


class TestTicketFingerprinterRealWorldScenarios:
    """Test realistic scenarios."""

    def test_support_updates_ticket_notes(self):
        """Support adding internal notes shouldn't change fingerprint."""
        # Initial ticket
        ticket_v1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I'm locked out",
        )

        fp_v1 = TicketFingerprinter.generate(ticket_v1)

        # Support adds internal note (not part of fingerprint content)
        ticket_v2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I'm locked out",
        )

        fp_v2 = TicketFingerprinter.generate(ticket_v2)

        # Content unchanged - fingerprint should match
        assert fp_v1 == fp_v2
        assert TicketFingerprinter.has_changed(ticket_v2, fp_v1) is False

    def test_customer_adds_details(self):
        """Customer adding details should change fingerprint."""
        # Initial ticket
        ticket_v1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I can't login",
        )

        fp_v1 = TicketFingerprinter.generate(ticket_v1)

        # Customer adds details
        ticket_v2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I can't login. I've tried resetting my password but it didn't work",
        )

        fp_v2 = TicketFingerprinter.generate(ticket_v2)

        # Content changed - fingerprint should differ
        assert fp_v1 != fp_v2
        assert TicketFingerprinter.has_changed(ticket_v2, fp_v1) is True

    def test_email_corrected_by_support(self):
        """Email correction should change fingerprint."""
        # Initial ticket with typo
        ticket_v1 = Ticket(
            id=1,
            name="Cannot login",
            email_from="joh@company.com",
        )

        fp_v1 = TicketFingerprinter.generate(ticket_v1)

        # Support corrects email
        ticket_v2 = Ticket(
            id=1,
            name="Cannot login",
            email_from="john@company.com",
        )

        fp_v2 = TicketFingerprinter.generate(ticket_v2)

        # Email changed - should re-evaluate
        assert fp_v1 != fp_v2
        assert TicketFingerprinter.has_changed(ticket_v2, fp_v1) is True
