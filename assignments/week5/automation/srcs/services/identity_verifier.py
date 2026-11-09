"""Identity verification service for P2 Issue #4.

POC training contract for requester verification.
NOT for production use. Demonstrates fail-closed verification boundary.

Email matching alone does NOT authorize account reactivation.
Verification must be explicit, with clear provenance and outcome.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Result of identity verification attempt."""

    VERIFIED = "verified"
    """Identity confirmed through trusted verification source."""

    UNVERIFIED = "unverified"
    """Identity not confirmed (email match insufficient)."""

    UNAVAILABLE = "unavailable"
    """Verification source not available or not configured."""

    FAILED = "failed"
    """Verification attempt failed (error during check)."""


@dataclass
class VerificationResult:
    """Result of an identity verification check."""

    status: VerificationStatus
    """Verification status."""

    reason: str
    """Human-readable explanation of the result."""

    source: str
    """Which verification source provided this result."""

    verified_email: Optional[str] = None
    """Verified email address (only if status is VERIFIED)."""


class IdentityVerifier:
    """POC training contract for identity verification.

    Demonstrates how to separate email matching from trusted verification.
    In production, would integrate with real identity providers (SAML, OAuth, etc.).

    For training: Uses explicit mock verification in tests.
    Never treats ENVIRONMENT=development or email match as automatic approval.
    """

    def __init__(self, verification_source: str = "mock_training_poc"):
        """Initialize verifier.

        Args:
            verification_source: Identifier for the verification source.
                                Typically "oauth", "saml", "ldap", or "mock_training_poc".
        """
        self.verification_source = verification_source
        logger.info(
            f"IdentityVerifier initialized with source: {verification_source} "
            "(POC training contract - NOT for production)"
        )

    def verify(self, ticket_email: str, employee_email: str) -> VerificationResult:
        """Verify that ticket requester is authorized to represent the employee.

        Email matching is NOT sufficient for authorization.
        Requires explicit verification through a trusted source.

        Args:
            ticket_email: Email from the ticket (claimed identity).
            employee_email: Email from HR system (employee record).

        Returns:
            VerificationResult with status, reason, and source.
        """
        try:
            # Step 1: Basic email matching (necessary but NOT sufficient)
            if not ticket_email or not employee_email:
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    reason="Email addresses missing - cannot verify identity.",
                    source=self.verification_source,
                )

            if ticket_email.lower() != employee_email.lower():
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    reason=f"Email mismatch: ticket email '{ticket_email}' does not match employee email '{employee_email}'.",
                    source=self.verification_source,
                )

            # Step 2: Email matches, but we need TRUSTED verification
            # In training with mock source: Verification is UNAVAILABLE (not configured)
            # In production: Would check SAML, OAuth, LDAP, etc.
            if self.verification_source == "mock_training_poc":
                return VerificationResult(
                    status=VerificationStatus.UNAVAILABLE,
                    reason=(
                        "Training POC: No real verification source available. "
                        "Email matched, but requires explicit trusted verification for approval. "
                        "In production, would verify via SAML/OAuth/LDAP."
                    ),
                    source=self.verification_source,
                )

            # If we get here with a non-POC source but no real integration,
            # fail closed
            return VerificationResult(
                status=VerificationStatus.UNAVAILABLE,
                reason=f"Verification source '{self.verification_source}' not properly configured.",
                source=self.verification_source,
            )

        except Exception as e:
            logger.error(f"Identity verification error: {str(e)}")
            return VerificationResult(
                status=VerificationStatus.FAILED,
                reason=f"Verification failed with error: {str(e)}",
                source=self.verification_source,
            )

    def verify_with_mock_approval(
        self, ticket_email: str, employee_email: str
    ) -> VerificationResult:
        """Training-only method: Verify with explicit mock approval.

        This method is ONLY for training tests that want to exercise the approved path.
        It simulates what a real verification provider would return.

        Production code must never call this.

        Args:
            ticket_email: Email from ticket.
            employee_email: Email from HR.

        Returns:
            VerificationResult with VERIFIED status (if emails match).
        """
        logger.warning(
            "TRAINING ONLY: verify_with_mock_approval called. "
            "This method should never be used in production."
        )

        # Still require email match
        if not ticket_email or not employee_email:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                reason="Email addresses missing.",
                source=self.verification_source,
            )

        if ticket_email.lower() != employee_email.lower():
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                reason=f"Email mismatch: '{ticket_email}' != '{employee_email}'.",
                source=self.verification_source,
            )

        # Emails match AND explicit mock approval granted
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason=f"Training mock: Identity verified (email matched: {ticket_email}).",
            source=self.verification_source,
            verified_email=ticket_email,
        )
