"""LoginWorkflow - Orchestrate complete login issue automation."""

import logging
from dataclasses import dataclass
from typing import Optional

from srcs.models import Ticket, Employee
from srcs.clients.odoo.ticket_client import TicketClient
from srcs.clients.hr.hr_client import HRClient
from srcs.services.ticket_analyzer import TicketAnalyzer
from srcs.services.decision_service import DecisionService, Decision

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    success: bool
    action_taken: str  # "account_reactivated", "escalated_manual_review", "skipped"
    message: str
    error_message: Optional[str] = None
    ticket_id: Optional[int] = None
    employee_id: Optional[str] = None


class LoginWorkflow:
    """Complete login issue automation workflow.

    Orchestrates:
    1. Ticket analysis (TicketAnalyzer)
    2. Employee lookup (HRClient)
    3. Business decision (DecisionService)
    4. Account action (HR status update)
    5. Ticket notification (TicketClient)
    """

    def __init__(
        self,
        ticket_client: TicketClient,
        hr_client: HRClient,
        ticket_analyzer: TicketAnalyzer,
    ):
        """Initialize workflow with dependencies.

        Args:
            ticket_client: Odoo ticket system client
            hr_client: HR system client
            ticket_analyzer: Ticket analysis service
        """
        self.ticket_client = ticket_client
        self.hr_client = hr_client
        self.ticket_analyzer = ticket_analyzer
        self.decision_service = DecisionService()

    def execute(self, ticket_id: int) -> WorkflowResult:
        """Execute complete automation workflow for a ticket.

        Args:
            ticket_id: Ticket ID from Odoo

        Returns:
            WorkflowResult with execution details
        """
        try:
            logger.info(f"Starting login automation workflow for ticket {ticket_id}")

            # Step 1: Fetch ticket from Odoo
            ticket = self.ticket_client.get_ticket(ticket_id)
            if ticket is None:
                logger.error(f"Ticket {ticket_id} not found in Odoo")
                return WorkflowResult(
                    success=False,
                    action_taken="error",
                    message="",
                    error_message=f"Ticket {ticket_id} not found in Odoo system",
                    ticket_id=ticket_id,
                )

            # Step 2: Analyze ticket for login issues
            analysis = self.ticket_analyzer.analyze(ticket)
            logger.info(
                f"Ticket {ticket_id} analysis: is_login_issue={analysis.is_login_issue}, "
                f"type={analysis.issue_type}, confidence={analysis.confidence}"
            )

            # Update ticket with analysis results
            ticket.is_login_issue = analysis.is_login_issue
            ticket.issue_type = analysis.issue_type

            # Step 3: Look up employee by email
            employee = None
            if ticket.email_from:
                employee = self.hr_client.get_employee_by_email(ticket.email_from)
                if employee:
                    logger.info(
                        f"Found employee: {employee.name} ({employee.email}) - "
                        f"status={employee.status.value}"
                    )

            # Step 4: Make business decision
            decision = self.decision_service.decide(employee, ticket)
            logger.info(f"Decision for ticket {ticket_id}: {decision.action.value}")

            # Step 5: Execute decision and return result
            return self._execute_decision(
                ticket, employee, analysis, decision
            )

        except Exception as e:
            logger.error(f"Workflow error for ticket {ticket_id}: {str(e)}")
            return WorkflowResult(
                success=False,
                action_taken="error",
                message="",
                error_message=f"Workflow error: {str(e)}",
                ticket_id=ticket_id,
            )

    def _execute_decision(
        self, ticket: Ticket, employee: Optional[Employee], analysis, decision
    ) -> WorkflowResult:
        """Execute the decision and perform necessary actions.

        Args:
            ticket: Ticket model
            employee: Employee model or None
            analysis: Analysis result from TicketAnalyzer
            decision: Decision result from DecisionService

        Returns:
            WorkflowResult
        """

        # Decision: APPROVE_REACTIVATION
        if decision.action == Decision.APPROVE_REACTIVATION:
            return self._handle_reactivation(ticket, employee, decision)

        # Decision: MANUAL_REVIEW
        elif decision.action == Decision.MANUAL_REVIEW:
            return self._handle_escalation(ticket, employee, decision)

        # Decision: SKIP
        elif decision.action == Decision.SKIP:
            return self._handle_skip(ticket)

        # Unknown decision
        else:
            logger.warning(f"Unknown decision action: {decision.action}")
            return self._handle_escalation(ticket, employee, decision)

    def _handle_reactivation(
        self, ticket: Ticket, employee: Employee, decision
    ) -> WorkflowResult:
        """Handle account reactivation for active employee.

        Args:
            ticket: Ticket
            employee: Employee
            decision: Decision result

        Returns:
            WorkflowResult
        """
        logger.info(f"Reactivating account for employee {employee.name}")

        # Update employee status in HR (mark as reactivated)
        success = self.hr_client.update_employee_status(
            employee_id=employee.employee_id,
            new_status="active",
        )

        if not success:
            logger.warning(f"Failed to update HR status for {employee.name}")
            # Post escalation note instead
            self.ticket_client.add_log(
                ticket_id=ticket.id,
                log_message=f"[Automation] Account reactivation approved for {employee.name}, "
                f"but HR system update failed. Requires manual verification.",
                is_internal=True,
            )
            return WorkflowResult(
                success=True,
                action_taken="escalated_manual_review",
                message=f"Account reactivation approved but HR update failed for {employee.name}",
                ticket_id=ticket.id,
                employee_id=employee.employee_id,
            )

        # Post internal note with success
        self.ticket_client.add_log(
            ticket_id=ticket.id,
            log_message=f"[Automation] Account reactivated for employee {employee.name} ({employee.email}). "
            f"Issue: {decision.reason}",
            is_internal=True,
        )
        
        self.ticket_client.update_stage(
            ticket_id=ticket.id,
            stage_id=4,
        )

        logger.info(f"✓ Account reactivation completed for ticket {ticket.id}")

        return WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message=f"Account successfully reactivated for {employee.name}",
            ticket_id=ticket.id,
            employee_id=employee.employee_id,
        )

    def _handle_escalation(
        self, ticket: Ticket, employee: Optional[Employee], decision
    ) -> WorkflowResult:
        """Handle escalation to manual review.

        Args:
            ticket: Ticket
            employee: Employee or None
            decision: Decision result

        Returns:
            WorkflowResult
        """
        employee_name = employee.name if employee else "Unknown"
        employee_id = employee.employee_id if employee else None

        logger.info(f"Escalating ticket {ticket.id} for manual review: {decision.reason}")

        # Post internal note with escalation reason
        self.ticket_client.add_log(
            ticket_id=ticket.id,
            log_message=f"[Automation] Escalated for manual review. {decision.reason}",
            is_internal=True,
        )

        return WorkflowResult(
            success=True,
            action_taken="escalated_manual_review",
            message=f"Ticket escalated for manual review: {decision.reason}",
            ticket_id=ticket.id,
            employee_id=employee_id,
        )

    def _handle_skip(self, ticket: Ticket) -> WorkflowResult:
        """Handle skipping non-applicable tickets.

        Args:
            ticket: Ticket

        Returns:
            WorkflowResult
        """
        logger.info(f"Skipping ticket {ticket.id} - not a login issue")

        return WorkflowResult(
            success=True,
            action_taken="skipped",
            message="Ticket is not a login issue. No automation applied.",
            ticket_id=ticket.id,
        )
