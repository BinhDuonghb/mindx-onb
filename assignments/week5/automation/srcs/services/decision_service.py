"""Decision service - Make deterministic business decisions on login automation."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from srcs.models import Employee, EmployeeStatus, Ticket

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

    This service implements deterministic decision rules:
    - Active employee + login issue + email match → Approve reactivation
    - Terminated/inactive/on-leave employee → Manual review
    - Email mismatch or missing → Manual review
    - No login issue → Skip
    - Employee not found → Manual review

    No external API calls are made here - decisions are based on provided data.
    """

    def decide(self, employee: Optional[Employee], ticket: Ticket) -> DecisionResult:
        """Make a decision for a login issue ticket.

        Args:
            employee: Employee model or None if not found
            ticket: Ticket model with classification

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

            # Rule 7: Active employee with login issue - APPROVE
            if employee.status == EmployeeStatus.ACTIVE:
                if employee.lms_account_status == "active":
                    return DecisionResult(
                        action=Decision.SKIP,
                        reason="LMS account is already active.",
                    )

                if employee.lms_account_status == "deactivated":
                    if employee.deactivation_reason == "inactivity_30_days":
                        return DecisionResult(
                            action=Decision.APPROVE_REACTIVATION,
                            reason=(
                                "Employee is active. LMS account was "
                                "deactivated due to 30 days of inactivity."
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
