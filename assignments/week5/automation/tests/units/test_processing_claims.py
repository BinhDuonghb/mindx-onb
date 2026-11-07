"""Test processing claims integration - RED phase.

Verify that processing claims are enforced before workflow execution to prevent
duplicate concurrent processing of the same ticket.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.services.ticket_fingerprinter import TicketFingerprinter
from srcs.models import Ticket, AutomationState, AutomationStatus


class TestProcessingClaimsIntegration:
    """Test processing claim enforcement in automation flow."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield Path(path)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    @pytest.fixture
    def repo(self, temp_db):
        """Create repository with temp database."""
        return AutomationStateRepository(db_path=temp_db)

    @pytest.fixture
    def ticket(self):
        """Create test ticket."""
        return Ticket(
            id=1,
            name="Cannot login",
            email_from="user@company.com",
            description="I cannot login to the system"
        )

    def test_new_ticket_can_be_claimed(self, repo, ticket):
        """New ticket should be claimable for processing."""
        fingerprint = TicketFingerprinter.generate(ticket)

        # Should succeed on first claim
        claimed = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )

        assert claimed is True

    def test_claimed_ticket_cannot_be_claimed_again(self, repo, ticket):
        """Already claimed ticket should not be claimable by another worker."""
        fingerprint = TicketFingerprinter.generate(ticket)

        # First claim succeeds
        claimed1 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed1 is True

        # Second claim fails (lease still active)
        claimed2 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed2 is False

    def test_expired_lease_can_be_recovered(self, repo, ticket):
        """Expired processing lease should be recoverable."""
        fingerprint = TicketFingerprinter.generate(ticket)

        # Claim with very short lease
        claimed1 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=0  # Already expired
        )
        assert claimed1 is True

        # Should be able to recover expired lease
        claimed2 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed2 is True

    def test_fingerprint_change_allows_reclaim(self, repo, ticket):
        """Fingerprint change allows re-evaluation only if lease has expired."""
        fingerprint1 = TicketFingerprinter.generate(ticket)

        # Claim with original fingerprint (very short lease)
        claimed1 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint1,
            lease_duration_seconds=0  # Already expired
        )
        assert claimed1 is True

        # Simulate ticket content change
        ticket.name = "Cannot login - updated"
        fingerprint2 = TicketFingerprinter.generate(ticket)

        # Should allow reclaim due to fingerprint change (lease expired)
        claimed2 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint2,
            lease_duration_seconds=300
        )
        assert claimed2 is True

    def test_fingerprint_change_cannot_bypass_active_lease(self, repo, ticket):
        """Fingerprint change cannot bypass an active processing lease."""
        fingerprint1 = TicketFingerprinter.generate(ticket)

        # Claim with original fingerprint (active lease)
        claimed1 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint1,
            lease_duration_seconds=300  # Active lease
        )
        assert claimed1 is True

        # Simulate ticket content change
        ticket.name = "Cannot login - updated"
        fingerprint2 = TicketFingerprinter.generate(ticket)

        # Should NOT allow reclaim (active lease prevents bypass)
        claimed2 = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint2,
            lease_duration_seconds=300
        )
        assert claimed2 is False

    def test_claim_preserves_side_effect_flags(self, repo, ticket):
        """Claim should preserve existing side-effect completion flags."""
        fingerprint = TicketFingerprinter.generate(ticket)

        # Create state with side-effect flags set
        state = AutomationState(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            status=AutomationStatus.PROCESSING,
            reactivation_completed=True,
            odoo_note_completed=True,
        )
        repo.save(state)

        # Claim should preserve flags
        claimed = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed is True

        # Verify flags are still set
        updated_state = repo.get(ticket.id)
        assert updated_state.reactivation_completed is True
        assert updated_state.odoo_note_completed is True

    def test_claim_does_not_reset_state_object(self, repo, ticket):
        """Claim should not replace state object, only update lease."""
        fingerprint = TicketFingerprinter.generate(ticket)

        # Create initial state
        original_state = AutomationState(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            status=AutomationStatus.COMPLETED,
            last_decision="account_reactivated",
            last_reason="Test reason",
        )
        repo.save(original_state)
        original_created_at = original_state.created_at

        # Claim should preserve original state
        claimed = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        assert claimed is True

        # Verify state is preserved
        retrieved_state = repo.get(ticket.id)
        assert retrieved_state.created_at == original_created_at
        assert retrieved_state.last_decision == "account_reactivated"
        assert retrieved_state.last_reason == "Test reason"

    def test_claim_sets_processing_lease_timestamp(self, repo, ticket):
        """Claim should set processing_lease_until timestamp."""
        fingerprint = TicketFingerprinter.generate(ticket)

        before_claim = datetime.now(timezone.utc)
        claimed = repo.claim_for_processing(
            ticket_id=ticket.id,
            fingerprint=fingerprint,
            lease_duration_seconds=300
        )
        after_claim = datetime.now(timezone.utc)

        assert claimed is True

        # Verify lease was set
        state = repo.get(ticket.id)
        assert state.processing_lease_until is not None
        # Lease should be approximately 300 seconds in the future
        lease_seconds = (state.processing_lease_until - after_claim).total_seconds()
        assert 290 < lease_seconds <= 310  # Allow small time variance

    def test_concurrent_tickets_independent_claims(self, repo):
        """Different tickets should have independent claim status."""
        ticket1 = Ticket(id=1, name="Issue 1", email_from="user1@company.com")
        ticket2 = Ticket(id=2, name="Issue 2", email_from="user2@company.com")

        fp1 = TicketFingerprinter.generate(ticket1)
        fp2 = TicketFingerprinter.generate(ticket2)

        # Claim ticket 1
        claimed1 = repo.claim_for_processing(ticket_id=1, fingerprint=fp1, lease_duration_seconds=300)
        assert claimed1 is True

        # Ticket 2 should be independently claimable
        claimed2 = repo.claim_for_processing(ticket_id=2, fingerprint=fp2, lease_duration_seconds=300)
        assert claimed2 is True

        # Ticket 1 still cannot be re-claimed
        claimed1_again = repo.claim_for_processing(ticket_id=1, fingerprint=fp1, lease_duration_seconds=300)
        assert claimed1_again is False
