"""LoginWorkflow - Orchestrate complete login issue automation."""

import logging
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from srcs.repositories.automation_state_repository import AutomationStateRepository
from srcs.models.automation_state import AutomationState
from srcs.models import Ticket, Employee
from srcs.clients.odoo.ticket_client import TicketClient
from srcs.clients.hr.hr_client import HRClient
from srcs.services.ticket_analyzer import TicketAnalyzer
from srcs.services.decision_service import DecisionService, Decision
from srcs.services.communication_state import CommunicationStateTracker
from srcs.services.gmail import CommunicationEvent

if TYPE_CHECKING:
    from srcs.services.gmail import GmailService

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    success: bool
    action_taken: str  # "account_reactivated", "escalated_manual_review", "skipped", "retry_scheduled", "error"
    message: str
    error_message: Optional[str] = None
    ticket_id: Optional[int] = None
    employee_id: Optional[str] = None

    # Side-effect completion flags (for retry scenarios)
    reactivation_completed: bool = False
    reactivation_authorized: bool = False
    odoo_note_completed: bool = False
    customer_response_completed: bool = False
    stage_update_completed: bool = False
    email_delivery_completed: bool = False  # P1-03: Track email delivery success separately

    # P2 Issue #5: Track ambiguous Odoo write outcomes
    ambiguous_write_outcome: Optional[str] = None  # e.g., "message_post:unknown", "write:unknown"


class LoginWorkflow:
    """Complete login issue automation workflow.

    Orchestrates:
    1. Ticket analysis (TicketAnalyzer)
    2. Employee lookup (HRClient)
    3. Business decision (DecisionService)
    4. Account action (HR status update)
    5. Ticket notification (TicketClient)
    6. Email notification (GmailService - optional)
    """

    def __init__(
        self,
        ticket_client: TicketClient,
        hr_client: HRClient,
        ticket_analyzer: TicketAnalyzer,
        gmail_service: Optional["GmailService"] = None,
        state_repo: Optional[AutomationStateRepository] = None,
        identity_verifier: Optional["IdentityVerifier"] = None,
    ):
        """Initialize workflow with dependencies.

        Args:
            ticket_client: Odoo ticket system client
            hr_client: HR system client
            ticket_analyzer: Ticket analysis service
            gmail_service: Optional email service for customer notifications
            state_repo: Optional repository for persistent communication state
            identity_verifier: Optional identity verifier (P2 Issue #4)
        """
        from srcs.services.identity_verifier import IdentityVerifier

        self.ticket_client = ticket_client
        self.hr_client = hr_client
        self.ticket_analyzer = ticket_analyzer
        self.gmail_service = gmail_service
        self.identity_verifier = identity_verifier or IdentityVerifier(verification_source="mock_training_poc")
        self.decision_service = DecisionService(verifier=self.identity_verifier)
        self.communication_state = CommunicationStateTracker(repo=state_repo)

    def execute(self, ticket_id: int, state: Optional[AutomationState] = None) -> WorkflowResult:
        """Execute complete automation workflow for a ticket.

        Args:
            ticket_id: Ticket ID from Odoo
            state: Optional previous AutomationState (for retry scenarios)

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

            # Step 2: Check if ticket has customer email (required for any automation)
            # P2 Issue #4: For login tickets, escalate to manual review if email missing
            # Don't silently skip - it might be a genuine request
            if ticket.email_from is None or not ticket.email_from.strip():
                # Analyze first to see if it's a login issue
                analysis = self.ticket_analyzer.analyze(ticket)
                ticket.is_login_issue = analysis.is_login_issue

                if analysis.is_login_issue:
                    # Login issue but no email - escalate for manual review
                    # P2 Issue #5 Task 1: Check for persisted UNKNOWN write outcome before posting note
                    if state and state.ambiguous_write_outcome:
                        logger.warning(
                            f"Login ticket {ticket_id} has no email and persisted ambiguous outcome: {state.ambiguous_write_outcome}. "
                            f"Cannot post note without manual review."
                        )
                        return WorkflowResult(
                            success=False,
                            action_taken="escalated_manual_review",
                            message="Ticket has no customer email and previous write attempt left ambiguous outcome. "
                                    "Escalating for manual review.",
                            error_message=f"Ambiguous write outcome: {state.ambiguous_write_context}",
                            ticket_id=ticket_id,
                            ambiguous_write_outcome=state.ambiguous_write_outcome,
                        )

                    # P2 Issue #4 Fix 1: Post a clear Odoo note explaining why manual review is required
                    logger.warning(f"Login ticket {ticket_id} has no customer email - escalating to manual review")

                    try:
                        note_success = self.ticket_client.add_log(
                            ticket_id=ticket_id,
                            log_message="[Automation] Login issue identified but ticket has no customer email. "
                            "Unable to verify employee identity. Escalated to manual review for verification and reactivation."
                        )

                        # A lost response is not evidence that Odoo did not create the note.
                        if note_success.is_unknown():
                            return WorkflowResult(
                                success=False,
                                action_taken="escalated_manual_review",
                                message="Odoo note outcome unknown; manual reconciliation required",
                                error_message=note_success.error or "Odoo note outcome unknown",
                                ticket_id=ticket_id,
                                ambiguous_write_outcome="message_post:unknown",
                            )
                        if not note_success.is_success():
                            return WorkflowResult(
                                success=False,
                                action_taken="retry_scheduled",
                                message="Login issue identified but failed to record escalation reason in Odoo",
                                error_message=note_success.error or "Failed to post manual review note",
                                ticket_id=ticket_id,
                            )
                    except Exception as e:
                        # The request might have been committed before the exception.
                        logger.warning(f"Uncertain Odoo note result for ticket {ticket_id}: {e}")
                        return WorkflowResult(
                            success=False,
                            action_taken="escalated_manual_review",
                            message="Odoo note result unconfirmed; manual reconciliation required",
                            error_message=str(e),
                            ticket_id=ticket_id,
                            ambiguous_write_outcome="message_post:unknown",
                        )

                    return WorkflowResult(
                        success=True,
                        action_taken="escalated_manual_review",
                        message="Login issue identified but ticket has no customer email. Escalated for manual review.",
                        ticket_id=ticket_id,
                        odoo_note_completed=True,
                    )
                else:
                    # Not a login issue and no email - safe to skip
                    logger.info(f"Skipping ticket {ticket_id}: no customer email and not a login issue")
                    return WorkflowResult(
                        success=True,
                        action_taken="skipped",
                        message="Ticket does not have customer email set and is not a login issue. No automation applied.",
                        ticket_id=ticket_id,
                    )

            # Step 3: Analyze ticket for login issues
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

            # Step 4: Make business decision (pass state for P1-01 fix: retry side-effect handling)
            decision = self.decision_service.decide(employee, ticket, state=state)
            logger.info(f"Decision for ticket {ticket_id}: {decision.action.value}")

            # Step 5: Execute decision (pass state for side-effect tracking)
            result = self._execute_decision(
                ticket, employee, analysis, decision, state
            )
            # The decision service may approve only via a VERIFIED identity
            # or a durable, previously authorized reactivation. Preserve the
            # authorization evidence even when downstream Odoo/email fails.
            if decision.action == Decision.APPROVE_REACTIVATION:
                result.reactivation_authorized = True

            # Step 6: Send exactly ONE appropriate email based on outcome
            # P1-03: Capture email send result for retry handling
            email_sent = self._send_outcome_email(ticket, employee, result)
            result.email_delivery_completed = email_sent

            return result

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
        self, ticket: Ticket, employee: Optional[Employee], analysis, decision,
        state: Optional["AutomationState"] = None
    ) -> WorkflowResult:
        """Execute the decision and perform necessary actions.

        Args:
            ticket: Ticket model
            employee: Employee model or None
            analysis: Analysis result from TicketAnalyzer
            decision: Decision result from DecisionService
            state: Optional previous AutomationState (for side-effect tracking)

        Returns:
            WorkflowResult
        """

        # Decision: APPROVE_REACTIVATION
        if decision.action == Decision.APPROVE_REACTIVATION:
            return self._handle_reactivation(ticket, employee, decision, state)

        # Decision: MANUAL_REVIEW
        elif decision.action == Decision.MANUAL_REVIEW:
            return self._handle_escalation(ticket, employee, decision, state)

        # Decision: SKIP
        elif decision.action == Decision.SKIP:
            return self._handle_skip(ticket)

        # Unknown decision
        else:
            logger.warning(f"Unknown decision action: {decision.action}")
            return self._handle_escalation(ticket, employee, decision, state)

    def _handle_reactivation(
        self, ticket: Ticket, employee: Employee, decision,
        state: Optional["AutomationState"] = None
    ) -> WorkflowResult:
        """Handle account reactivation for active employee.

        Tracks side effects and skips already-completed actions on retry.

        P2 Issue #5 Task 1: If a previous execution left message_post:unknown,
        do not attempt add_log() again automatically. Escalate to manual review instead.

        Args:
            ticket: Ticket
            employee: Employee
            decision: Decision result
            state: Optional previous AutomationState (for side-effect tracking)

        Returns:
            WorkflowResult
        """
        logger.info(f"Reactivating account for employee {employee.name}")

        # P2 Issue #5 Task 1: Check for persisted UNKNOWN write outcome
        # If previous execution left ambiguous_write_outcome, do not retry the write automatically
        if state and state.ambiguous_write_outcome:
            logger.warning(
                f"Ticket {ticket.id} has persisted ambiguous outcome: {state.ambiguous_write_outcome}. "
                f"Cannot safely retry without manual review."
            )
            return WorkflowResult(
                success=False,
                action_taken="escalated_manual_review",
                message=f"Previous write attempt left ambiguous outcome ({state.ambiguous_write_outcome}). "
                        f"Escalating for manual review to prevent duplicate operations.",
                error_message=f"Ambiguous write outcome: {state.ambiguous_write_context}",
                ticket_id=ticket.id,
                employee_id=employee.employee_id,
                reactivation_completed=state.reactivation_completed,
                odoo_note_completed=state.odoo_note_completed,
                stage_update_completed=state.stage_update_completed,
                ambiguous_write_outcome=state.ambiguous_write_outcome,
            )

        # Step 1: Reactivate LMS account (skip if already completed)
        reactivation_completed = state and state.reactivation_completed

        if reactivation_completed:
            logger.info(f"LMS reactivation already completed for ticket {ticket.id}, skipping")
        else:
            success = self.hr_client.reactivate_lms_account(
                employee_id=employee.employee_id,
                new_status="active",
            )

            if not success:
                logger.warning(f"Failed to reactivate LMS account for {employee.name}")
                # Schedule retry instead of escalating
                from srcs.repositories.automation_state_repository import AutomationStateRepository
                # This would be called by main.py after saving state
                # Mark for retry with error message
                return WorkflowResult(
                    success=False,
                    action_taken="retry_scheduled",
                    message=f"LMS reactivation failed for {employee.name}",
                    error_message="LMS system update failed",
                    ticket_id=ticket.id,
                    employee_id=employee.employee_id,
                )

            reactivation_completed = True

        # Step 2: Post internal note (skip if already completed)
        odoo_note_completed = state and state.odoo_note_completed

        if odoo_note_completed:
            logger.info(f"Odoo note already posted for ticket {ticket.id}, skipping")
        else:
            try:
                outcome = self.ticket_client.add_log(
                    ticket_id=ticket.id,
                    log_message=f"[Automation] Account reactivated for employee {employee.name} ({employee.email}). "
                    f"Issue: {decision.reason}",
                )

                # P2 Issue #5: Handle three outcome types
                if outcome.is_success():
                    odoo_note_completed = True
                    logger.info(f"Successfully posted Odoo note for ticket {ticket.id}")
                elif outcome.is_unknown():
                    # Unknown outcome: server may have committed the note
                    # Persist ambiguous state and escalate to manual review
                    logger.warning(f"Ambiguous Odoo note outcome for ticket {ticket.id}: {outcome.error}")
                    if state:
                        state.ambiguous_write_outcome = "message_post:unknown"
                        state.ambiguous_write_context = outcome.error
                    return WorkflowResult(
                        success=False,
                        action_taken="escalated_manual_review",
                        message=f"Ambiguous Odoo note outcome for ticket {ticket.id}",
                        error_message=f"Unknown write outcome: {outcome.error}",
                        ticket_id=ticket.id,
                        employee_id=employee.employee_id,
                        reactivation_completed=reactivation_completed,
                        ambiguous_write_outcome="message_post:unknown",
                    )
                else:
                    # Confirmed failure
                    logger.warning(f"Odoo add_log failed (confirmed) for ticket {ticket.id}: {outcome.error}")
                    return WorkflowResult(
                        success=False,
                        action_taken="retry_scheduled",
                        message=f"Failed to post Odoo note for ticket {ticket.id}",
                        error_message=outcome.error,
                        ticket_id=ticket.id,
                        employee_id=employee.employee_id,
                        reactivation_completed=reactivation_completed,
                    )

            except Exception as e:
                logger.warning(f"Uncertain Odoo note result for ticket {ticket.id}: {e}")
                return WorkflowResult(
                    success=False,
                    action_taken="escalated_manual_review",
                    message="Odoo note result unconfirmed; manual reconciliation required",
                    error_message=str(e),
                    ticket_id=ticket.id,
                    employee_id=employee.employee_id,
                    reactivation_completed=reactivation_completed,
                    ambiguous_write_outcome="message_post:unknown",
                )

        # Step 3: Update ticket stage (skip if already completed)
        stage_update_completed = state and state.stage_update_completed

        if stage_update_completed:
            logger.info(f"Stage update already completed for ticket {ticket.id}, skipping")
        else:
            # P2 Issue #4: Use configurable stage mapping instead of hardcoded stage_id=4
            from srcs import config

            stage_id = config.ODOO_STAGE_MAPPING.get("awaiting_confirmation", 0)
            if stage_id == 0 or stage_id in config.ODOO_STAGE_DONE_IDS:
                logger.error(
                    f"Odoo awaiting_confirmation stage missing or mapped to a known Done stage. "
                    f"Set ODOO_STAGE_AWAITING_CONFIRMATION in .env. "
                    f"Cannot update ticket {ticket.id} stage without configuration."
                )
                # Fail closed: Don't proceed without proper configuration
                return WorkflowResult(
                    success=False,
                    action_taken="retry_scheduled",
                    message="Odoo stage mapping not configured",
                    error_message="ODOO_STAGE_AWAITING_CONFIRMATION not set in configuration",
                    ticket_id=ticket.id,
                    employee_id=employee.employee_id,
                    reactivation_completed=reactivation_completed,
                    odoo_note_completed=odoo_note_completed,
                )

            try:
                outcome = self.ticket_client.update_stage(
                    ticket_id=ticket.id,
                    stage_id=stage_id,
                )

                # P2 Issue #5: Handle three outcome types
                if outcome.is_success():
                    stage_update_completed = True
                    logger.info(f"Successfully updated stage for ticket {ticket.id}")
                elif outcome.is_unknown():
                    # Unknown outcome: server may have committed the stage update
                    # Persist ambiguous state and escalate to manual review
                    logger.warning(f"Ambiguous stage update outcome for ticket {ticket.id}: {outcome.error}")
                    if state:
                        state.ambiguous_write_outcome = "write:unknown"
                        state.ambiguous_write_context = outcome.error
                    return WorkflowResult(
                        success=False,
                        action_taken="escalated_manual_review",
                        message=f"Ambiguous stage update outcome for ticket {ticket.id}",
                        error_message=f"Unknown write outcome: {outcome.error}",
                        ticket_id=ticket.id,
                        employee_id=employee.employee_id,
                        reactivation_completed=reactivation_completed,
                        odoo_note_completed=odoo_note_completed,
                        ambiguous_write_outcome="write:unknown",
                    )
                else:
                    # Confirmed failure
                    logger.warning(f"Odoo update_stage failed (confirmed) for ticket {ticket.id}: {outcome.error}")
                    return WorkflowResult(
                        success=False,
                        action_taken="retry_scheduled",
                        message=f"Failed to update ticket stage",
                        error_message=outcome.error,
                        ticket_id=ticket.id,
                        employee_id=employee.employee_id,
                        reactivation_completed=reactivation_completed,
                        odoo_note_completed=odoo_note_completed,
                    )

            except Exception as e:
                logger.warning(f"Uncertain Odoo stage update for ticket {ticket.id}: {e}")
                return WorkflowResult(
                    success=False,
                    action_taken="escalated_manual_review",
                    message="Odoo stage update unconfirmed; manual reconciliation required",
                    error_message=str(e),
                    ticket_id=ticket.id,
                    employee_id=employee.employee_id,
                    reactivation_completed=reactivation_completed,
                    odoo_note_completed=odoo_note_completed,
                    ambiguous_write_outcome="write:unknown",
                )

        logger.info(f"✓ Account reactivation completed for ticket {ticket.id}")

        # Build result with side-effect completion flags for caller to persist
        result = WorkflowResult(
            success=True,
            action_taken="account_reactivated",
            message=f"Account successfully reactivated for {employee.name}",
            ticket_id=ticket.id,
            employee_id=employee.employee_id,
        )

        # Store side-effect flags in result for caller to persist
        result.reactivation_completed = reactivation_completed
        result.odoo_note_completed = odoo_note_completed
        result.stage_update_completed = stage_update_completed

        return result

    def _handle_escalation(
        self, ticket: Ticket, employee: Optional[Employee], decision,
        state: Optional["AutomationState"] = None
    ) -> WorkflowResult:
        """Handle escalation to manual review.

        P2 Issue #5 Task 1: Check for persisted UNKNOWN write outcome before posting note.
        If previous add_log() left ambiguous outcome, do not attempt to post another note.

        Args:
            ticket: Ticket
            employee: Employee or None
            decision: Decision result
            state: Optional previous AutomationState (for UNKNOWN guard)

        Returns:
            WorkflowResult
        """
        employee_name = employee.name if employee else "Unknown"
        employee_id = employee.employee_id if employee else None

        logger.info(f"Escalating ticket {ticket.id} for manual review: {decision.reason}")

        # P2 Issue #5 Task 1: Check for persisted UNKNOWN write outcome
        # If previous execution left ambiguous_write_outcome, do not attempt add_log() again
        if state and state.ambiguous_write_outcome:
            logger.warning(
                f"Ticket {ticket.id} has persisted ambiguous outcome: {state.ambiguous_write_outcome}. "
                f"Cannot post escalation note without manual review."
            )
            return WorkflowResult(
                success=False,
                action_taken="escalated_manual_review",
                message=f"Previous write attempt left ambiguous outcome ({state.ambiguous_write_outcome}). "
                        f"Escalating for manual review.",
                error_message=f"Ambiguous write outcome: {state.ambiguous_write_context}",
                ticket_id=ticket.id,
                employee_id=employee_id,
                ambiguous_write_outcome=state.ambiguous_write_outcome,
            )

        # Post internal note with escalation reason
        # P2 Issue #5: Handle explicit write outcomes
        try:
            outcome = self.ticket_client.add_log(
                ticket_id=ticket.id,
                log_message=f"[Automation] Escalated for manual review. {decision.reason}",
            )

            # If note posting failed, don't report successful escalation
            if outcome.is_unknown():
                logger.warning(f"Ambiguous note outcome for escalation on ticket {ticket.id}")
                return WorkflowResult(
                    success=False,
                    action_taken="escalated_manual_review",
                    message="Failed to record escalation reason in Odoo (ambiguous outcome)",
                    error_message=outcome.error,
                    ticket_id=ticket.id,
                    employee_id=employee_id,
                    ambiguous_write_outcome="message_post:unknown",
                )
            elif not outcome.is_success():
                logger.warning(f"Failed to post Odoo note for escalation on ticket {ticket.id}")
                return WorkflowResult(
                    success=False,
                    action_taken="retry_scheduled",
                    message="Failed to record escalation reason in Odoo",
                    error_message=outcome.error,
                    ticket_id=ticket.id,
                    employee_id=employee_id,
                )
        except Exception as e:
            logger.warning(f"Uncertain escalation note result for ticket {ticket.id}: {e}")
            return WorkflowResult(
                success=False,
                action_taken="escalated_manual_review",
                message="Odoo escalation note result unconfirmed; manual reconciliation required",
                error_message=str(e),
                ticket_id=ticket.id,
                employee_id=employee_id,
                ambiguous_write_outcome="message_post:unknown",
            )

        # Email will be sent by caller
        return WorkflowResult(
            success=True,
            action_taken="escalated_manual_review",
            message=f"Ticket escalated for manual review: {decision.reason}",
            ticket_id=ticket.id,
            employee_id=employee_id,
            odoo_note_completed=True,
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

    def _send_acknowledgement(self, ticket: Ticket) -> None:
        """Send acknowledgement email for new login issue ticket.

        Only sends if not previously sent (deduplication via CommunicationStateTracker).

        Args:
            ticket: Ticket that was identified as a login issue
        """
        if not self.gmail_service or not ticket.email_from:
            return

        # Check if ACK already sent for this ticket
        if not self.communication_state.should_send(ticket.id, CommunicationEvent.TICKET_RECEIVED):
            logger.info(f"ACK already sent for ticket {ticket.id}, skipping duplicate")
            return

        from srcs.services.gmail import EmailContext, EmailTemplate

        email_context = EmailContext(
            recipient_email=ticket.email_from,
            recipient_name=ticket.email_from.split("@")[0],  # Simple name fallback
            ticket_id=ticket.id,
            ticket_title=ticket.name,
            template=EmailTemplate.ACKNOWLEDGEMENT,
        )

        email_sent = self.gmail_service.send_email(email_context)
        if email_sent:
            # Mark as sent in communication state
            self.communication_state.mark_sent(ticket.id, CommunicationEvent.TICKET_RECEIVED)
            logger.info(f"Acknowledgement email sent to {ticket.email_from}")
        else:
            logger.warning(f"Failed to send acknowledgement email to {ticket.email_from}")

    def _send_outcome_email(
        self, ticket: Ticket, employee: Optional[Employee], result: WorkflowResult
    ) -> bool:
        """Send exactly ONE appropriate email based on workflow outcome.

        Communication Policy:
        - account_reactivated → RESOLUTION email
        - escalated_manual_review → MANUAL_REVIEW email
        - skipped → no email
        - error → no email

        TASK 2 FIX: Catch SMTP exceptions safely without losing completed side-effect flags.
        Both send_email() returning False and raising exceptions are treated as retryable failures.

        Args:
            ticket: Ticket model
            employee: Employee model or None
            result: WorkflowResult with action taken

        Returns:
            True if email sent successfully (or no email needed), False if email send failed
        """
        if result.action_taken not in ("account_reactivated", "escalated_manual_review"):
            # Intentionally skipped: no email was delivered. Runner does not
            # retry emails for skipped/error/retry outcomes.
            logger.info(f"Outcome email intentionally skipped for: {result.action_taken}")
            return False

        if not self.gmail_service or not ticket.email_from:
            logger.warning(
                "Outcome email NOT delivered for ticket %s: %s",
                ticket.id,
                "SMTP not configured" if not self.gmail_service else "recipient email missing",
            )
            return False  # Never report an unsent outcome email as delivered.

        from srcs.services.gmail import EmailContext, EmailTemplate

        # Determine which email to send based on outcome
        if result.action_taken == "account_reactivated":
            # Success: Send RESOLUTION email
            event = CommunicationEvent.REACTIVATION_SUCCESSFUL
            template = EmailTemplate.RESOLUTION
            recipient_name = employee.name if employee else "User"

        elif result.action_taken == "escalated_manual_review":
            # Escalation: Send MANUAL_REVIEW email
            event = CommunicationEvent.MANUAL_REVIEW_REQUIRED
            template = EmailTemplate.MANUAL_REVIEW
            recipient_name = employee.name if employee else "User"

        else:
            # Skipped or error: No email (treat as success - no action required)
            logger.info(f"No email for outcome: {result.action_taken}")
            return True

        # Check if this email was already sent for this ticket
        if not self.communication_state.should_send(ticket.id, event):
            logger.info(f"Email event {event.value} already sent for ticket {ticket.id}, skipping duplicate")
            return True  # Already sent - treat as success

        # Build email context
        email_context = EmailContext(
            recipient_email=ticket.email_from,
            recipient_name=recipient_name,
            ticket_id=ticket.id,
            ticket_title=ticket.name,
            template=template,
        )

        try:
            # TASK 2 FIX: Send email and catch exceptions
            email_sent = self.gmail_service.send_email(email_context)
            if email_sent:
                self.communication_state.mark_sent(ticket.id, event)
                logger.info(f"Outcome email ({template.value}) sent to {ticket.email_from}")
                return True
            else:
                logger.warning(f"Failed to send outcome email ({template.value}) to {ticket.email_from}")
                return False  # Retryable failure

        except Exception as e:
            # TASK 2 FIX: Catch SMTP and other exceptions - treat as retryable failure
            logger.warning(f"Exception sending outcome email ({template.value}) to {ticket.email_from}: {str(e)}")
            return False  # Retryable failure (do not propagate exception)
