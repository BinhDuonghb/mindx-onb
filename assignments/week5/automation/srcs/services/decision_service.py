"""Decision service - Make deterministic business decisions on login automation."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from srcs.models import Employee, EmployeeStatus, DeactivationReason, Ticket, AutomationState, AutomationStatus
from srcs.services.identity_verifier import IdentityVerifier, VerificationStatus

logger = logging.getLogger(__name__)


class Decision(str, Enum):
    """Possible automation decisions."""

    APPROVE_REACTIVATION = "approve_reactivation"
    MANUAL_REVIEW = "manual_review"
    SKIP = "skip"
    RETRY_OR_ESCALATE = "retry_or_escalate"


@dataclass
class DecisionResult:
    """Result of a decision."""

    action: Decision
    reason: str


class DecisionService:
    """Make business logic decisions for login issue automation.

    P2 Issue #4: Email matching alone does NOT authorize reactivation.
    Requires explicit trusted identity verification.

    This service implements deterministic decision rules:
    - Active employee + login issue + EMAIL MATCH + VERIFIED IDENTITY → Approve reactivation
    - Verified identity unavailable or failed → Manual review (fail closed)
    - Terminated/inactive/on-leave employee → Manual review
    - Email mismatch or missing → Manual review
    - No login issue → Skip
    - Employee not found → Manual review

    No external API calls are made here - decisions are based on provided data.
    """

    def __init__(self, verifier: Optional[IdentityVerifier] = None):
        """Initialize decision service.

        Args:
            verifier: Identity verifier (typically a mock in training).
                     If None, creates a default POC verifier.
        """
        self.verifier = verifier or IdentityVerifier(verification_source="mock_training_poc")

    def decide(
        self, employee: Optional[Employee], ticket: Ticket,
        state: Optional[AutomationState] = None
    ) -> DecisionResult:
        """Make a decision for a login issue ticket.

        Args:
            employee: Employee model or None if not found
            ticket: Ticket model with classification
            state: Optional previous AutomationState to check for pending operations

        Returns:
            DecisionResult with action and reason
        """
        try:
            # Rule 1: Employee not found
            if employee is None:
                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason="Employee not found in HR system. Requires manual review.",
                )

            # Rule 2: Not a login issue
            if not ticket.is_login_issue:
                return DecisionResult(
                    action=Decision.SKIP,
                    reason=f"Ticket is not a login issue (classified as: {ticket.issue_type or 'unknown'}). Skipping automation.",
                )

            # Rule 3: Email mismatch or missing
            if not ticket.email_from or not ticket.email_from.strip():
                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason="Ticket has no customer email. Unable to verify employee identity. Requires manual review.",
                )

            if ticket.email_from.lower() != employee.email.lower():
                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason=f"Email mismatch: ticket email '{ticket.email_from}' does not match employee email '{employee.email}'. Requires manual review.",
                )

            # Rule 4: Terminated employee
            if employee.status == EmployeeStatus.TERMINATED:
                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason=f"Employee '{employee.name}' has been terminated. Account reactivation not approved. Requires manual review.",
                )

            # Rule 5: On-leave employee
            if employee.status == EmployeeStatus.ON_LEAVE:
                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason=f"Employee '{employee.name}' is currently on leave. Account reactivation deferred. Requires manual review.",
                )

            # Rule 6: Inactive employee
            if employee.status == EmployeeStatus.INACTIVE:
                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason=f"Employee '{employee.name}' has inactive status. Account reactivation requires manual review.",
                )

            # Rule 7: Active employee with login issue
            # P2 Issue #4: Require verified identity in addition to email match
            if employee.status == EmployeeStatus.ACTIVE:
                if employee.lms_account_status == "active":
                    # P1-01 Fix: Check for pending operations before skipping
                    # P1-03 Fix: Also check for pending email delivery
                    # If this is a retry with incomplete side effects, continue workflow
                    pending_effects = state and (
                        not state.odoo_note_completed
                        or not state.stage_update_completed
                        or not state.email_delivery_completed
                    )
                    # An active LMS account, pending effects, or a retry status do
                    # NOT prove that the requester was authorized. The approval
                    # evidence is written only after a VERIFIED decision and
                    # persisted together with the completed LMS reactivation.
                    if pending_effects:
                        if (
                            state.reactivation_authorized
                            and state.reactivation_completed
                            and state.status in (AutomationStatus.RETRY_SCHEDULED, AutomationStatus.PROCESSING)
                            and not state.ambiguous_write_outcome
                        ):
                            return DecisionResult(
                                action=Decision.APPROVE_REACTIVATION,
                                reason="Previously authorized LMS reactivation completed; resuming remaining side effects.",
                            )
                        return DecisionResult(
                            action=Decision.MANUAL_REVIEW,
                            reason="Pending operations without durable prior approval and completed reactivation. Manual verification required.",
                        )

                    return DecisionResult(
                        action=Decision.SKIP,
                        reason="LMS account is already active.",
                    )

                if employee.lms_account_status == "deactivated":
                    if employee.deactivation_reason == DeactivationReason.INACTIVITY_30_DAYS:
                        # P2 Issue #4: Verify identity before approving reactivation
                        verification = self.verifier.verify(ticket.email_from, employee.email)

                        if verification.status == VerificationStatus.VERIFIED:
                            return DecisionResult(
                                action=Decision.APPROVE_REACTIVATION,
                                reason=(
                                    f"Employee is active and identity verified. LMS account was "
                                    "deactivated due to 30 days of inactivity. Approval granted."
                                ),
                            )
                        elif verification.status == VerificationStatus.UNVERIFIED:
                            return DecisionResult(
                                action=Decision.MANUAL_REVIEW,
                                reason=f"Identity verification failed: {verification.reason}. Requires manual review.",
                            )
                        else:
                            # UNAVAILABLE or FAILED - fail closed
                            return DecisionResult(
                                action=Decision.MANUAL_REVIEW,
                                reason=(
                                    f"Identity verification {verification.status.value}: {verification.reason} "
                                    "Cannot automatically approve reactivation without verified identity. Requires manual review."
                                ),
                            )

                    return DecisionResult(
                        action=Decision.MANUAL_REVIEW,
                        reason="Unsupported LMS deactivation reason.",
                    )

                return DecisionResult(
                    action=Decision.MANUAL_REVIEW,
                    reason="Unknown LMS account status.",
                )

            # Fallback: Unknown status
            return DecisionResult(
                action=Decision.MANUAL_REVIEW,
                reason=f"Employee status '{employee.status}' is unknown. Requires manual review.",
            )

        except Exception as e:
            logger.error(f"Error making decision for ticket {ticket.id}: {str(e)}")
            return DecisionResult(
                action=Decision.MANUAL_REVIEW,
                reason=f"Error during decision-making: {str(e)}. Escalated for manual review.",
            )
