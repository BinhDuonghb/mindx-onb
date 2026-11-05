"""End-to-end tests for LoginWorkflow with real Odoo and mock HR system.

These tests execute the complete automation workflow against real tickets
in the test Odoo instance, using a mocked HR system to avoid modifying
production HR data.

Run with:
    pytest tests/e2e/test_login_workflow_e2e.py -v -s
"""

import pytest
import logging
from unittest.mock import Mock
from srcs.clients.odoo.ticket_client import TicketClient
from srcs.clients.hr.hr_client import HRClient
from srcs.services.ticket_analyzer import TicketAnalyzer
from srcs.services.login_workflow import LoginWorkflow
from srcs.models import Employee, EmployeeStatus
from srcs.config import ACTIVE_ODOO_URL, ACTIVE_ODOO_DATABASE, ACTIVE_ODOO_RPC_KEY

logger = logging.getLogger(__name__)


@pytest.fixture
def real_ticket_client():
    """Create real TicketClient connected to test Odoo."""
    headers = {
        "Authorization": f"Bearer {ACTIVE_ODOO_RPC_KEY}",
        "Content-Type": "application/json",
    }

    api_endpoint = f"{ACTIVE_ODOO_URL}/json/2"

    client = TicketClient(
        api_endpoint=api_endpoint,
        database=ACTIVE_ODOO_DATABASE,
        headers=headers,
        timeout=30,
        max_retries=1,
    )

    logger.info(f"Connected to real Odoo: {ACTIVE_ODOO_URL}")

    yield client

    client.close()


@pytest.fixture
def mock_hr_client():
    """Create mock HR client with predefined employee data."""
    client = Mock(spec=HRClient)

    # Define mock employees for different scenarios
    active_employee = Employee(
        employee_id="EMP001",
        name="Test User",
        email="duongdznhat98@gmail.com",
        status=EmployeeStatus.ACTIVE,
        department="Engineering",
        lms_account_status="deactivated",
        deactivation_reason="inactivity_30_days"
    )

    terminated_employee = Employee(
        employee_id="EMP002",
        name="Terminated User",
        email="duonghb1577@gmail.com",
        status=EmployeeStatus.TERMINATED,
        department="Sales",
        lms_account_status="deactivated",
        deactivation_reason="Employee terminated"
    )

    # Setup mock responses
    def get_employee_by_email_side_effect(email):
        """Return mock employee based on email."""
        if email == "duongdznhat98@gmail.com":
            return active_employee
        elif email == "duonghb1577@gmail.com":
            return terminated_employee
        return None

    client.get_employee_by_email.side_effect = get_employee_by_email_side_effect
    client.reactivate_lms_account.return_value = True

    logger.info("Created mock HR client with predefined employees")

    return client


@pytest.fixture
def ticket_analyzer():
    """Create ticket analyzer instance."""
    return TicketAnalyzer()


@pytest.fixture
def workflow(real_ticket_client, mock_hr_client, ticket_analyzer):
    """Create LoginWorkflow with real Odoo and mock HR."""
    return LoginWorkflow(
        ticket_client=real_ticket_client,
        hr_client=mock_hr_client,
        ticket_analyzer=ticket_analyzer,
    )


class TestLoginWorkflowWithRealOdoo:
    """Test LoginWorkflow against real Odoo tickets."""

    def test_ticket_3_login_issue_workflow(self, workflow, real_ticket_client, mock_hr_client):
        """Execute workflow for ticket 3 (real Odoo ticket)."""
        logger.info("Starting workflow test for ticket 3")

        # Get ticket from real Odoo
        ticket = real_ticket_client.get_ticket(3)

        if ticket is None:
            pytest.skip("Ticket 3 not found in Odoo instance")

        logger.info(f"Found ticket 3: {ticket.name}")
        logger.info(f"Email: {ticket.email_from}")
        logger.info(f"Content: {ticket.description[:100] if ticket.description else 'No description'}")

        # Execute workflow - should succeed regardless of pattern detection
        result = workflow.execute(ticket_id=3)

        logger.info(f"Workflow result: action={result.action_taken}, success={result.success}")

        # Verify execution completed without error
        assert result.success is True
        assert result.ticket_id == 3
        assert result.action_taken in ["account_reactivated", "escalated_manual_review", "skipped"]

        logger.info(f"✓ Workflow executed for ticket 3: {result.action_taken}")

    def test_ticket_4_login_issue_workflow(self, workflow, real_ticket_client, mock_hr_client):
        """Execute workflow for ticket 4 (real Odoo ticket)."""
        logger.info("Starting workflow test for ticket 4")

        # Get ticket from real Odoo
        ticket = real_ticket_client.get_ticket(4)

        if ticket is None:
            pytest.skip("Ticket 4 not found in Odoo instance")

        logger.info(f"Found ticket 4: {ticket.name}")
        logger.info(f"Email: {ticket.email_from}")
        logger.info(f"Content: {ticket.description[:100] if ticket.description else 'No description'}")

        # Execute workflow - should succeed regardless of pattern detection
        result = workflow.execute(ticket_id=4)

        logger.info(f"Workflow result: action={result.action_taken}, success={result.success}")

        # Verify execution completed without error
        assert result.success is True
        assert result.ticket_id == 4
        assert result.action_taken in ["account_reactivated", "escalated_manual_review", "skipped"]

        logger.info(f"✓ Workflow executed for ticket 4: {result.action_taken}")

    def test_workflow_decision_flow_for_ticket_3(
        self, workflow, real_ticket_client, mock_hr_client
    ):
        """Verify analysis and decision flow for ticket 3."""
        logger.info("Testing analysis flow for ticket 3")

        ticket = real_ticket_client.get_ticket(3)

        if ticket is None:
            pytest.skip("Ticket 3 not found")

        # Analyze ticket (will detect what it finds)
        analyzer = workflow.ticket_analyzer
        analysis = analyzer.analyze(ticket)

        logger.info(
            f"Analysis: is_login_issue={analysis.is_login_issue}, "
            f"type={analysis.issue_type}, reason={analysis.reason}"
        )

        # Verify analysis completed and returned result
        assert analysis is not None
        assert hasattr(analysis, "is_login_issue")
        assert hasattr(analysis, "issue_type")
        assert hasattr(analysis, "reason")
        assert hasattr(analysis, "confidence")
        assert 0.0 <= analysis.confidence <= 1.0

        logger.info(f"✓ Ticket 3 analysis completed: {analysis.reason}")

    def test_workflow_decision_flow_for_ticket_4(
        self, workflow, real_ticket_client, mock_hr_client
    ):
        """Verify analysis and decision flow for ticket 4."""
        logger.info("Testing analysis flow for ticket 4")

        ticket = real_ticket_client.get_ticket(4)

        if ticket is None:
            pytest.skip("Ticket 4 not found")

        # Analyze ticket (will detect what it finds)
        analyzer = workflow.ticket_analyzer
        analysis = analyzer.analyze(ticket)

        logger.info(
            f"Analysis: is_login_issue={analysis.is_login_issue}, "
            f"type={analysis.issue_type}, reason={analysis.reason}"
        )

        # Verify analysis completed and returned result
        assert analysis is not None
        assert hasattr(analysis, "is_login_issue")
        assert hasattr(analysis, "issue_type")
        assert hasattr(analysis, "reason")
        assert hasattr(analysis, "confidence")
        assert 0.0 <= analysis.confidence <= 1.0

        logger.info(f"✓ Ticket 4 analysis completed: {analysis.reason}")

    def test_tickets_retrieved_from_real_odoo(self, real_ticket_client):
        """Verify we can retrieve tickets from real Odoo."""
        logger.info("Verifying real Odoo connectivity")

        # Try to get both tickets
        ticket_3 = real_ticket_client.get_ticket(3)
        ticket_4 = real_ticket_client.get_ticket(4)

        # At least one should exist
        has_tickets = ticket_3 is not None or ticket_4 is not None

        if not has_tickets:
            pytest.skip("Neither ticket 3 nor 4 found in Odoo instance")

        if ticket_3:
            logger.info(f"✓ Ticket 3: {ticket_3.name}")
        if ticket_4:
            logger.info(f"✓ Ticket 4: {ticket_4.name}")


class TestLoginWorkflowAnalysisPatterns:
    """Test pattern analysis on real Odoo tickets."""

    def test_analyzer_on_ticket_3(self, workflow, real_ticket_client):
        """Verify analyzer can process ticket 3 without errors."""
        ticket = real_ticket_client.get_ticket(3)

        if ticket is None:
            pytest.skip("Ticket 3 not found")

        analyzer = workflow.ticket_analyzer
        analysis = analyzer.analyze(ticket)

        logger.info(f"Ticket 3 analysis: is_login={analysis.is_login_issue}, reason={analysis.reason}")

        # Verify analysis completed successfully
        assert analysis is not None
        assert hasattr(analysis, "is_login_issue")
        assert isinstance(analysis.is_login_issue, bool)

    def test_analyzer_on_ticket_4(self, workflow, real_ticket_client):
        """Verify analyzer can process ticket 4 without errors."""
        ticket = real_ticket_client.get_ticket(4)

        if ticket is None:
            pytest.skip("Ticket 4 not found")

        analyzer = workflow.ticket_analyzer
        analysis = analyzer.analyze(ticket)

        logger.info(f"Ticket 4 analysis: is_login={analysis.is_login_issue}, reason={analysis.reason}")

        # Verify analysis completed successfully
        assert analysis is not None
        assert hasattr(analysis, "is_login_issue")
        assert isinstance(analysis.is_login_issue, bool)


class TestEndToEndIntegration:
    """Test complete end-to-end flow."""

    def test_complete_workflow_cycle_with_ticket_3(
        self, workflow, real_ticket_client, mock_hr_client
    ):
        """Complete workflow: fetch → analyze → decide → execute for ticket 3."""
        logger.info("=== Starting complete E2E workflow for ticket 3 ===")

        ticket = real_ticket_client.get_ticket(3)

        if ticket is None:
            pytest.skip("Ticket 3 not found in Odoo")

        logger.info(f"Step 1: Fetched ticket 3: '{ticket.name}'")
        logger.info(f"  Email: {ticket.email_from}")
        logger.info(f"  Description: {ticket.description}")

        # Execute workflow
        result = workflow.execute(ticket_id=3)

        logger.info(f"Step 2-5: Workflow executed")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Action: {result.action_taken}")
        logger.info(f"  Message: {result.message}")

        # Verify workflow succeeded
        assert result.success is True
        assert result.ticket_id == 3

        logger.info("=== E2E workflow for ticket 3 completed successfully ===")

    def test_complete_workflow_cycle_with_ticket_4(
        self, workflow, real_ticket_client, mock_hr_client
    ):
        """Complete workflow: fetch → analyze → decide → execute for ticket 4."""
        logger.info("=== Starting complete E2E workflow for ticket 4 ===")

        ticket = real_ticket_client.get_ticket(4)

        if ticket is None:
            pytest.skip("Ticket 4 not found in Odoo")

        logger.info(f"Step 1: Fetched ticket 4: '{ticket.name}'")
        logger.info(f"  Email: {ticket.email_from}")
        logger.info(f"  Description: {ticket.description}")

        # Execute workflow
        result = workflow.execute(ticket_id=4)

        logger.info(f"Step 2-5: Workflow executed")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Action: {result.action_taken}")
        logger.info(f"  Message: {result.message}")

        # Verify workflow succeeded
        assert result.success is True
        assert result.ticket_id == 4

        logger.info("=== E2E workflow for ticket 4 completed successfully ===")
