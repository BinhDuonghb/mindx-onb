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
from datetime import datetime

# Load configuration
try:
    from srcs.config import (
        ODOO_API_ENDPOINT,
        ODOO_DATABASE,
        ODOO_HEADERS,
        LOG_LEVEL,
        HR_FILE,
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

    def __init__(self):
        """Initialize executor with clients and services."""
        try:
            # Import here to avoid circular imports and allow graceful error handling
            from srcs.clients.odoo.ticket_client import TicketClient
            from srcs.clients.hr.hr_client import HRClient
            from srcs.repositories.automation_state_repository import AutomationStateRepository
            from srcs.services.ticket_poller import TicketPoller, PollingMetrics
            from srcs.services.login_workflow import LoginWorkflow
            from srcs.services.ticket_analyzer import TicketAnalyzer
            from srcs.services.decision_service import DecisionService

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

            # Initialize workflow
            self.workflow = LoginWorkflow(
                ticket_client=self.ticket_client,
                hr_client=self.hr_client,
                ticket_analyzer=self.ticket_analyzer,
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
            start_time = datetime.utcnow()

            # Poll for tickets
            logger.info(f"Polling for tickets (limit={limit})...")
            tickets = self.poller.poll(limit=limit, min_age_minutes=min_age_minutes)

            if not tickets:
                logger.info("No tickets to process")
                return {
                    "success": True,
                    "tickets_processed": 0,
                    "successful": 0,
                    "escalated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "elapsed_seconds": (datetime.utcnow() - start_time).total_seconds(),
                }

            logger.info(f"Processing {len(tickets)} tickets")

            # Process each ticket
            results = {
                "successful": 0,
                "escalated": 0,
                "skipped": 0,
                "failed": 0,
            }

            for i, ticket in enumerate(tickets, 1):
                try:
                    logger.info(f"Processing ticket {ticket.id} ({i}/{len(tickets)})")

                    # Execute workflow
                    result = self.workflow.execute(ticket_id=ticket.id)

                    # Save automation state after processing
                    self._save_ticket_state(ticket, result)

                    # Track result
                    if result.success:
                        if result.action_taken == "skipped":
                            results["skipped"] += 1
                        elif result.action_taken == "escalated_manual_review":
                            results["escalated"] += 1
                        elif result.action_taken == "account_reactivated":
                            results["successful"] += 1
                    else:
                        results["failed"] += 1
                        logger.error(f"Ticket {ticket.id} failed: {result.error_message}")

                except Exception as e:
                    logger.error(f"Exception processing ticket {ticket.id}: {str(e)}", exc_info=True)
                    results["failed"] += 1

            # Record metrics
            self.metrics.record_poll(
                fetched=len(tickets),
                queued=results["successful"] + results["escalated"],
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            results["success"] = True
            results["tickets_processed"] = len(tickets)
            results["elapsed_seconds"] = elapsed

            logger.info(
                f"One-time run complete: {results['successful']} successful, "
                f"{results['escalated']} escalated, {results['skipped']} skipped, "
                f"{results['failed']} failed in {elapsed:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"One-time run failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "elapsed_seconds": (datetime.utcnow() - start_time).total_seconds(),
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
                logger.info(f"--- Poll {poll_count} at {datetime.utcnow().isoformat()} ---")

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

    def _save_ticket_state(self, ticket, result) -> None:
        """Save automation state after processing a ticket.

        Args:
            ticket: Ticket model
            result: WorkflowResult from workflow execution
        """
        try:
            from srcs.models import AutomationState, AutomationStatus
            from srcs.services.ticket_fingerprinter import TicketFingerprinter

            # Determine status based on workflow result
            if result.action_taken == "account_reactivated":
                status = AutomationStatus.COMPLETED
            elif result.action_taken == "escalated_manual_review":
                status = AutomationStatus.MANUAL_REVIEW
            elif result.action_taken == "skipped":
                status = AutomationStatus.SKIPPED
            elif result.action_taken == "error":
                status = AutomationStatus.FAILED
            else:
                status = AutomationStatus.COMPLETED

            # Generate fingerprint for change detection
            fingerprint = TicketFingerprinter.generate(ticket)

            # Create and save state
            state = AutomationState(
                ticket_id=ticket.id,
                fingerprint=fingerprint,
                status=status,
                last_decision=result.action_taken,
                last_reason=result.message,
            )

            self.state_repo.save(state)
            logger.debug(f"Saved automation state for ticket {ticket.id}: status={status.value}")

        except Exception as e:
            logger.error(f"Failed to save automation state for ticket {ticket.id}: {str(e)}")
            # Don't raise - processing succeeded, just state saving failed


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
    logger.info(f"Started at {datetime.utcnow().isoformat()}")
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
