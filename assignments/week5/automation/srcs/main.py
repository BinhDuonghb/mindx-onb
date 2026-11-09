"""Main entry point for Odoo login issue automation.

Orchestrates the complete automation workflow:
1. Poll Odoo for new/updated tickets
2. Process each ticket through automation engine
3. Persist state for retry/tracking
4. Support both one-time and continuous polling modes

Usage:
    python main.py --once                    # Single poll and process
    python main.py --poll --interval 60      # Continuous polling every 60s
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Load configuration
try:
    from srcs.config import (
        ODOO_API_ENDPOINT,
        ODOO_DATABASE,
        ODOO_HEADERS,
        LOG_LEVEL,
        HR_FILE,
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USERNAME,
        SMTP_PASSWORD,
        SMTP_FROM_EMAIL,
    )
except ImportError as e:
    print(f"ERROR: Failed to load configuration: {e}")
    print("Ensure .env file exists in srcs/ directory with required variables:")
    print("  - ODOO_URL")
    print("  - ODOO_DATABASE")
    print("  - ODOO_RPC_KEY")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class AutomationExecutor:
    """Executes the complete automation workflow."""

    def __init__(self, ticket_client=None, hr_client=None, ticket_analyzer=None,
                 gmail_service=None, state_repo=None):
        """Initialize executor with clients and services.

        Args:
            ticket_client: Optional mocked ticket client for testing
            hr_client: Optional mocked HR client for testing
            ticket_analyzer: Optional mocked ticket analyzer for testing
            gmail_service: Optional mocked Gmail service for testing
            state_repo: Optional mocked state repository for testing
        """
        try:
            # If dependencies are provided (for testing), use them directly
            if ticket_client is not None:
                self.ticket_client = ticket_client
                self.hr_client = hr_client
                self.ticket_analyzer = ticket_analyzer
                self.gmail_service = gmail_service
                self.state_repo = state_repo
                self.poller = None  # For testing, we don't need poller
                self.decision_service = None
                self.workflow = None
                self.metrics = None
                return

            # Import here to avoid circular imports and allow graceful error handling
            from srcs.clients.odoo.ticket_client import TicketClient
            from srcs.clients.hr.hr_client import HRClient
            from srcs.repositories.automation_state_repository import AutomationStateRepository
            from srcs.services.ticket_poller import TicketPoller, PollingMetrics
            from srcs.services.login_workflow import LoginWorkflow
            from srcs.services.ticket_analyzer import TicketAnalyzer
            from srcs.services.decision_service import DecisionService
            from srcs.services.gmail import GmailService

            # Initialize Odoo ticket client
            self.ticket_client = TicketClient(
                api_endpoint=ODOO_API_ENDPOINT,
                database=ODOO_DATABASE,
                headers=ODOO_HEADERS,
            )

            # Initialize HR client
            self.hr_client = HRClient(file_path=HR_FILE)

            # Initialize analyzer
            self.ticket_analyzer = TicketAnalyzer()

            # Initialize decision service
            self.decision_service = DecisionService()

            # Initialize repository
            self.state_repo = AutomationStateRepository(
                db_path=Path("data/automation_state.db")
            )

            # Initialize poller
            self.poller = TicketPoller(
                ticket_client=self.ticket_client,
                state_repo=self.state_repo,
            )

            # Initialize Gmail service if credentials available
            gmail_service = None
            if SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM_EMAIL:
                try:
                    gmail_service = GmailService(
                        smtp_host=SMTP_HOST,
                        smtp_port=SMTP_PORT,
                        smtp_username=SMTP_USERNAME,
                        smtp_password=SMTP_PASSWORD,
                        from_email=SMTP_FROM_EMAIL,
                    )
                    logger.info("Gmail service initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize Gmail service: {str(e)}. Continuing without email support.")
            else:
                logger.warning("Gmail credentials not configured. Email notifications will be disabled.")

            # Initialize workflow with optional email service and persistent state repo
            self.workflow = LoginWorkflow(
                ticket_client=self.ticket_client,
                hr_client=self.hr_client,
                ticket_analyzer=self.ticket_analyzer,
                gmail_service=gmail_service,
                state_repo=self.state_repo,
            )

            # Metrics
            self.metrics = PollingMetrics()

            logger.info("Automation executor initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize executor: {str(e)}", exc_info=True)
            raise

    def run_once(self, limit: int = 50, min_age_minutes: int = 5) -> dict:
        """Run automation once: fetch and process tickets.

        Args:
            limit: Maximum tickets to fetch
            min_age_minutes: Minimum ticket age before processing

        Returns:
            Results summary
        """
        logger.info("Starting one-time automation run")

        try:
            start_time = datetime.now(timezone.utc)

            # Poll for new and changed tickets
            logger.info(f"Polling for new/changed tickets (limit={limit})...")
            tickets = self.poller.poll(limit=limit, min_age_minutes=min_age_minutes)

            # Poll for retry-scheduled tickets whose retry time has arrived
            logger.info(f"Polling for due retries (limit={limit})...")
            retry_tickets = self.poller.poll_for_retry(limit=limit)

            # TASK 4 FIX: Poll for expired PROCESSING tickets to recover orphaned work
            logger.info(f"Polling for expired processing leases (limit={limit})...")
            expired_tickets = []
            for expired_state in self.state_repo.get_expired_processing_tickets(limit=limit):
                try:
                    ticket = self.ticket_client.get_ticket(expired_state.ticket_id)
                    if ticket:
                        expired_tickets.append((ticket, expired_state))
                        logger.info(
                            f"Found expired processing ticket {expired_state.ticket_id} "
                            f"(lease expired at {expired_state.processing_lease_until})"
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch expired ticket {expired_state.ticket_id}: {str(e)}")
                    # Continue processing other expired tickets

            # Merge and deduplicate ticket IDs across all sources
            ticket_ids = set()
            all_tickets = []

            for ticket in tickets:
                if ticket.id not in ticket_ids:
                    ticket_ids.add(ticket.id)
                    all_tickets.append(ticket)

            # poll_for_retry() returns (ticket, state) tuples - extract just tickets
            for ticket, state in retry_tickets:
                if ticket.id not in ticket_ids:
                    ticket_ids.add(ticket.id)
                    all_tickets.append(ticket)

            # TASK 4 FIX: Also include expired processing tickets (for recovery)
            for ticket, state in expired_tickets:
                if ticket.id not in ticket_ids:
                    ticket_ids.add(ticket.id)
                    all_tickets.append(ticket)

            if not all_tickets:
                logger.info("No tickets to process")
                return {
                    "success": True,
                    "tickets_processed": 0,
                    "successful": 0,
                    "escalated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "elapsed_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                }

            logger.info(f"Processing {len(all_tickets)} tickets ({len(tickets)} new/changed, {len(retry_tickets)} retries)")

            # Process each ticket
            results = {
                "successful": 0,
                "escalated": 0,
                "skipped": 0,
                "failed": 0,
                "persistence_failures": 0,
                "error_details": [],
            }

            for i, ticket in enumerate(all_tickets, 1):
                try:
                    logger.info(f"Processing ticket {ticket.id} ({i}/{len(all_tickets)})")

                    # Generate fingerprint for claim
                    from srcs.services.ticket_fingerprinter import TicketFingerprinter
                    fingerprint = TicketFingerprinter.generate(ticket)

                    # Attempt to claim ticket for processing (prevents concurrent execution)
                    # TASK 3 FIX: claim_for_processing now returns ownership token (or None if claim fails)
                    # ISSUE 4 FIX: Distinguish legitimate contention (None) from SQLite failures (exception)
                    try:
                        owner_token = self.state_repo.claim_for_processing(
                            ticket_id=ticket.id,
                            fingerprint=fingerprint,
                            lease_duration_seconds=300  # 5 minute lease
                        )
                    except Exception as e:
                        logger.error(f"Exception claiming ticket {ticket.id}: {str(e)}", exc_info=True)
                        results["failed"] += 1
                        results["persistence_failures"] += 1
                        results["error_details"].append(
                            f"ticket {ticket.id}: claim_for_processing() raised {type(e).__name__}: {str(e)}"
                        )
                        continue

                    if not owner_token:
                        logger.info(
                            f"Ticket {ticket.id} already being processed by another worker, skipping"
                        )
                        results["skipped"] += 1
                        continue

                    # Load existing state for retry scenarios (preserves side-effect flags)
                    existing_state = self.state_repo.get(ticket.id)

                    # Execute workflow (pass state for side-effect tracking on retries)
                    result = self.workflow.execute(ticket_id=ticket.id, state=existing_state)

                    # Save automation state after processing
                    # ISSUE 2 FIX: Pass owner_token for atomic SQL validation
                    # ISSUE 4 FIX: Check return value - if save fails, don't proceed with result counting
                    save_success = self._save_ticket_state(ticket, result, owner_token=owner_token)
                    if not save_success:
                        logger.error(f"Failed to persist state for ticket {ticket.id}, marking as failed")
                        results["failed"] += 1
                        results["persistence_failures"] += 1
                        results["error_details"].append(
                            f"ticket {ticket.id}: save() failed"
                        )
                        continue

                    # Handle retry scheduling if workflow indicates failure
                    if result.action_taken == "retry_scheduled":
                        # ISSUE 4 FIX: Check return value of schedule_retry()
                        try:
                            retry_scheduled = self.state_repo.schedule_retry(
                                ticket_id=ticket.id,
                                retry_after_seconds=3600,  # Retry after 1 hour
                                error=result.error_message,
                                owner_token=owner_token  # ISSUE 2 FIX: Pass owner token
                            )
                            if retry_scheduled is False:
                                logger.error(f"Failed to schedule retry for ticket {ticket.id}")
                                results["failed"] += 1
                                results["persistence_failures"] += 1
                                results["error_details"].append(
                                    f"ticket {ticket.id}: schedule_retry() failed"
                                )
                            else:
                                results["failed"] += 1
                                logger.info(f"Scheduled retry for ticket {ticket.id}: {result.error_message}")
                        except Exception as e:
                            logger.error(f"Exception scheduling retry for ticket {ticket.id}: {str(e)}", exc_info=True)
                            results["failed"] += 1
                            results["persistence_failures"] += 1
                            results["error_details"].append(
                                f"ticket {ticket.id}: schedule_retry() raised {type(e).__name__}: {str(e)}"
                            )
                        continue

                    # P1-03: Handle email delivery failure - schedule retry for email only
                    if result.action_taken == "account_reactivated" and not result.email_delivery_completed:
                        logger.warning(f"Email delivery failed for ticket {ticket.id}, scheduling retry")
                        # ISSUE 4 FIX: Check return value of schedule_retry()
                        try:
                            email_retry_scheduled = self.state_repo.schedule_retry(
                                ticket_id=ticket.id,
                                retry_after_seconds=300,  # Retry sooner for email failures (5 minutes)
                                error="Email delivery failed - will retry",
                                owner_token=owner_token  # ISSUE 2 FIX: Pass owner token
                            )
                            if email_retry_scheduled is False:
                                logger.error(f"Failed to schedule email retry for ticket {ticket.id}")
                                results["failed"] += 1
                                results["persistence_failures"] += 1
                                results["error_details"].append(
                                    f"ticket {ticket.id}: schedule_retry() failed for email retry"
                                )
                            else:
                                results["failed"] += 1
                        except Exception as e:
                            logger.error(f"Exception scheduling email retry for ticket {ticket.id}: {str(e)}", exc_info=True)
                            results["failed"] += 1
                            results["persistence_failures"] += 1
                            results["error_details"].append(
                                f"ticket {ticket.id}: schedule_retry() raised {type(e).__name__} for email retry: {str(e)}"
                            )
                        continue

                    # ISSUE #2 FINAL FIX: Release lease after terminal workflow outcomes
                    # Terminal outcomes: COMPLETED, MANUAL_REVIEW, SKIPPED
                    if result.action_taken == "account_reactivated":
                        # Successful completion - release lease
                        # ISSUE 4 FIX: Check return value of mark_completed()
                        try:
                            mark_result = self.state_repo.mark_completed(ticket_id=ticket.id, owner_token=owner_token)
                            if mark_result is False:
                                logger.error(f"Failed to mark ticket {ticket.id} as completed - lease may not be released")
                                results["failed"] += 1
                                results["persistence_failures"] += 1
                                results["error_details"].append(
                                    f"ticket {ticket.id}: mark_completed() failed"
                                )
                            else:
                                results["successful"] += 1
                                logger.info(f"Completed and released lease for ticket {ticket.id}")
                        except Exception as e:
                            logger.error(f"Exception marking ticket {ticket.id} as completed: {str(e)}", exc_info=True)
                            results["failed"] += 1
                            results["persistence_failures"] += 1
                            results["error_details"].append(
                                f"ticket {ticket.id}: mark_completed() raised {type(e).__name__}: {str(e)}"
                            )
                    elif result.action_taken == "escalated_manual_review":
                        # Manual review escalation - release lease
                        # ISSUE 4 FIX: Check return value of mark_manual_review()
                        try:
                            review_result = self.state_repo.mark_manual_review(
                                ticket_id=ticket.id,
                                reason="Escalated to manual review",
                                owner_token=owner_token
                            )
                            if review_result is False:
                                logger.error(f"Failed to mark ticket {ticket.id} as manual review - lease may not be released")
                                results["failed"] += 1
                                results["persistence_failures"] += 1
                                results["error_details"].append(
                                    f"ticket {ticket.id}: mark_manual_review() failed"
                                )
                            else:
                                results["escalated"] += 1
                                logger.info(f"Escalated to manual review and released lease for ticket {ticket.id}")
                        except Exception as e:
                            logger.error(f"Exception marking ticket {ticket.id} as manual review: {str(e)}", exc_info=True)
                            results["failed"] += 1
                            results["persistence_failures"] += 1
                            results["error_details"].append(
                                f"ticket {ticket.id}: mark_manual_review() raised {type(e).__name__}: {str(e)}"
                            )
                    elif result.action_taken == "skipped":
                        # Ticket skipped - release lease
                        # ISSUE 4 FIX: Check return value of mark_skipped()
                        try:
                            skip_result = self.state_repo.mark_skipped(ticket_id=ticket.id, owner_token=owner_token)
                            if skip_result is False:
                                logger.error(f"Failed to mark ticket {ticket.id} as skipped - lease may not be released")
                                results["failed"] += 1
                                results["persistence_failures"] += 1
                                results["error_details"].append(
                                    f"ticket {ticket.id}: mark_skipped() failed"
                                )
                            else:
                                results["skipped"] += 1
                                logger.info(f"Skipped and released lease for ticket {ticket.id}")
                        except Exception as e:
                            logger.error(f"Exception marking ticket {ticket.id} as skipped: {str(e)}", exc_info=True)
                            results["failed"] += 1
                            results["persistence_failures"] += 1
                            results["error_details"].append(
                                f"ticket {ticket.id}: mark_skipped() raised {type(e).__name__}: {str(e)}"
                            )
                    else:
                        # Handle any other terminal outcome
                        if result.success:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                            logger.error(f"Ticket {ticket.id} failed: {result.error_message}")


                except Exception as e:
                    logger.error(f"Exception processing ticket {ticket.id}: {str(e)}", exc_info=True)
                    results["failed"] += 1

            # Record metrics
            self.metrics.record_poll(
                fetched=len(all_tickets),
                queued=results["successful"] + results["escalated"],
            )

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            results["success"] = results["persistence_failures"] == 0
            results["tickets_processed"] = len(all_tickets)
            results["elapsed_seconds"] = elapsed

            logger.info(
                f"One-time run complete: {results['successful']} successful, "
                f"{results['escalated']} escalated, {results['skipped']} skipped, "
                f"{results['failed']} failed, {results['persistence_failures']} persistence failures in {elapsed:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"One-time run failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "elapsed_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }

    def run_continuous(
        self,
        interval_seconds: int = 60,
        limit: int = 50,
        min_age_minutes: int = 5,
    ) -> None:
        """Run automation continuously with polling interval.

        Args:
            interval_seconds: Seconds between polls
            limit: Maximum tickets per poll
            min_age_minutes: Minimum ticket age before processing
        """
        logger.info(
            f"Starting continuous polling (interval={interval_seconds}s, limit={limit})"
        )

        poll_count = 0

        try:
            while True:
                poll_count += 1
                logger.info(f"--- Poll {poll_count} at {datetime.now(timezone.utc).isoformat()} ---")

                # Run one cycle
                result = self.run_once(limit=limit, min_age_minutes=min_age_minutes)

                if result.get("success"):
                    logger.info(
                        f"Poll {poll_count} results: {result.get('tickets_processed', 0)} "
                        f"processed ({result.get('successful', 0)} success, "
                        f"{result.get('escalated', 0)} escalated, "
                        f"{result.get('skipped', 0)} skipped)"
                    )
                else:
                    logger.error(f"Poll {poll_count} failed: {result.get('error', 'unknown error')}")

                # Wait before next poll
                logger.info(f"Waiting {interval_seconds}s before next poll...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Polling interrupted by user")
        except Exception as e:
            logger.error(f"Continuous polling failed: {str(e)}", exc_info=True)
            raise

    def get_metrics(self) -> dict:
        """Get polling metrics.

        Returns:
            Metrics dictionary
        """
        return self.metrics.to_dict()

    def _save_ticket_state(self, ticket, result, owner_token: str = None) -> bool:
        """Save automation state after processing a ticket.

        Updates existing state, preserving side-effect flags and retry metadata.

        Args:
            ticket: Ticket model
            result: WorkflowResult from workflow execution
            owner_token: Optional ownership token from claim_for_processing() for atomic SQL validation

        Returns:
            True if state was successfully persisted, False otherwise
        """
        try:
            from srcs.models import AutomationState, AutomationStatus
            from srcs.services.ticket_fingerprinter import TicketFingerprinter

            # ISSUE #4 FINAL FIX: Do NOT determine terminal status here
            # Keep status as PROCESSING and let repository transitions (schedule_retry, mark_*)
            # atomically establish final status after side effects persist.
            # This prevents orphaned records if a transition fails.

            # Generate fingerprint for change detection
            fingerprint = TicketFingerprinter.generate(ticket)

            # Load existing state to preserve side-effect flags and retry metadata
            existing_state = self.state_repo.get(ticket.id)

            if existing_state:
                # Update fingerprint and side-effect flags from workflow result
                # ISSUE #4 FINAL FIX: Do NOT change status - keep it as PROCESSING
                existing_state.fingerprint = fingerprint
                existing_state.last_decision = result.action_taken
                existing_state.last_reason = result.message

                # Persist side-effect completion flags from workflow result
                if result.reactivation_completed:
                    existing_state.reactivation_completed = True
                if result.odoo_note_completed:
                    existing_state.odoo_note_completed = True
                if result.customer_response_completed:
                    existing_state.customer_response_completed = True
                if result.stage_update_completed:
                    existing_state.stage_update_completed = True
                if result.email_delivery_completed:
                    existing_state.email_delivery_completed = True

                # Keep existing status - don't transition here
                state = existing_state
            else:
                # Create new state if none exists
                # ISSUE #4 FINAL FIX: Start in PROCESSING status, not terminal status
                state = AutomationState(
                    ticket_id=ticket.id,
                    fingerprint=fingerprint,
                    status=AutomationStatus.PROCESSING,  # Always start as PROCESSING
                    last_decision=result.action_taken,
                    last_reason=result.message,
                    reactivation_completed=result.reactivation_completed,
                    odoo_note_completed=result.odoo_note_completed,
                    customer_response_completed=result.customer_response_completed,
                    stage_update_completed=result.stage_update_completed,
                    email_delivery_completed=result.email_delivery_completed,
                )

            # ISSUE #4 FIX: Check return value of save()
            save_result = self.state_repo.save(state, owner_token=owner_token)
            if save_result is False:
                logger.error(f"Failed to persist automation state for ticket {ticket.id}: save() returned False")
                return False

            logger.debug(f"Saved automation state for ticket {ticket.id}: preserved side effects")
            return True

        except Exception as e:
            logger.error(f"Failed to save automation state for ticket {ticket.id}: {str(e)}", exc_info=True)
            # ISSUE #4 FIX: Return False on exception instead of silently continuing
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Odoo login issue automation - processes recurring login problem tickets",
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run automation once and exit",
    )
    mode_group.add_argument(
        "--poll",
        action="store_true",
        help="Run automation continuously with polling interval",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds (default: 60)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum tickets to fetch per poll (default: 50)",
    )

    parser.add_argument(
        "--min-age",
        type=int,
        default=5,
        help="Minimum ticket age in minutes before processing (default: 5)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    logger.info("=" * 80)
    logger.info("Odoo Login Issue Automation")
    logger.info(f"Started at {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 80)

    try:
        # Initialize executor
        executor = AutomationExecutor()

        # Run in selected mode
        if args.once:
            logger.info("Mode: ONE-TIME RUN")
            result = executor.run_once(limit=args.limit, min_age_minutes=args.min_age)
            print("\nResults:")
            for key, value in result.items():
                print(f"  {key}: {value}")
            sys.exit(0 if result.get("success") else 1)

        elif args.poll:
            logger.info("Mode: CONTINUOUS POLLING")
            executor.run_continuous(
                interval_seconds=args.interval,
                limit=args.limit,
                min_age_minutes=args.min_age,
            )

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
