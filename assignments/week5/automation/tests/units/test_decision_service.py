"""Unit tests for DecisionService - Make business decisions on login issue automation."""

import pytest
from srcs.services.decision_service import DecisionService, Decision
from srcs.models import Employee, EmployeeStatus, Ticket


@pytest.fixture
def service():
    """Create a DecisionService instance."""
    return DecisionService()


class TestDecisionServiceActiveEmployee:
    """Test decisions for active employees."""

    def test_active_employee_with_login_issue_is_approved(self, service):
        """Active employee with login issue should be approved for reactivation."""
        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
            department="Engineering",
        )

        ticket = Ticket(
            id=1,
            name="Cannot login",
            email_from="john@company.com",
            is_login_issue=True,
            issue_type="cannot_login",
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.APPROVE_REACTIVATION
        assert decision.reason is not None

    def test_active_employee_without_login_issue_is_skipped(self, service):
        """Active employee with non-login issue should be skipped."""
        employee = Employee(
            employee_id="EMP001",
            name="John Doe",
            email="john@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=1,
            name="General question",
            email_from="john@company.com",
            is_login_issue=False,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.SKIP
        assert decision.reason is not None


class TestDecisionServiceTerminatedEmployee:
    """Test decisions for terminated employees."""

    def test_terminated_employee_is_escalated(self, service):
        """Terminated employee should be escalated for manual review."""
        employee = Employee(
            employee_id="EMP002",
            name="Jane Smith",
            email="jane@company.com",
            status=EmployeeStatus.TERMINATED,
        )

        ticket = Ticket(
            id=2,
            name="Cannot login",
            email_from="jane@company.com",
            is_login_issue=True,
            issue_type="cannot_login",
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.MANUAL_REVIEW
        assert "terminated" in decision.reason.lower()


class TestDecisionServiceOnLeaveEmployee:
    """Test decisions for on-leave employees."""

    def test_onleave_employee_is_escalated(self, service):
        """On-leave employee should be escalated."""
        employee = Employee(
            employee_id="EMP003",
            name="Bob Johnson",
            email="bob@company.com",
            status=EmployeeStatus.ON_LEAVE,
        )

        ticket = Ticket(
            id=3,
            name="Cannot login",
            email_from="bob@company.com",
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.MANUAL_REVIEW
        assert "leave" in decision.reason.lower()


class TestDecisionServiceInactiveEmployee:
    """Test decisions for inactive employees."""

    def test_inactive_employee_is_escalated(self, service):
        """Inactive employee should be escalated."""
        employee = Employee(
            employee_id="EMP004",
            name="Alice Brown",
            email="alice@company.com",
            status=EmployeeStatus.INACTIVE,
        )

        ticket = Ticket(
            id=4,
            name="Cannot login",
            email_from="alice@company.com",
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.MANUAL_REVIEW


class TestDecisionServiceEmailMismatch:
    """Test decisions when email doesn't match."""

    def test_email_mismatch_is_escalated(self, service):
        """Mismatched email should be escalated for manual review."""
        employee = Employee(
            employee_id="EMP005",
            name="Charlie Davis",
            email="charlie@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=5,
            name="Cannot login",
            email_from="different@company.com",  # Different email
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.MANUAL_REVIEW
        assert "email" in decision.reason.lower() or "mismatch" in decision.reason.lower()

    def test_missing_ticket_email_is_escalated(self, service):
        """Ticket with missing email should be escalated."""
        employee = Employee(
            employee_id="EMP006",
            name="Eve Thompson",
            email="eve@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=6,
            name="Cannot login",
            email_from="",  # Missing email
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.MANUAL_REVIEW
        assert "email" in decision.reason.lower()


class TestDecisionServiceNoneEmployee:
    """Test decisions when employee is not found."""

    def test_employee_not_found_is_escalated(self, service):
        """Unknown employee should be escalated."""
        ticket = Ticket(
            id=7,
            name="Cannot login",
            email_from="unknown@company.com",
            is_login_issue=True,
        )

        decision = service.decide(None, ticket)

        assert decision.action == Decision.MANUAL_REVIEW
        assert "not found" in decision.reason.lower()


class TestDecisionServiceDecisionFields:
    """Test Decision result structure."""

    def test_decision_has_required_fields(self, service):
        """Decision should have all required fields."""
        employee = Employee(
            employee_id="EMP007",
            name="Frank Wilson",
            email="frank@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=8,
            name="Cannot login",
            email_from="frank@company.com",
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert hasattr(decision, "action")
        assert hasattr(decision, "reason")
        assert decision.reason is not None
        assert len(decision.reason) > 0


class TestDecisionServiceDeterminism:
    """Test that decisions are deterministic."""

    def test_same_input_same_decision(self, service):
        """Same inputs should always produce same decision."""
        employee = Employee(
            employee_id="EMP008",
            name="Grace Lee",
            email="grace@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=9,
            name="Cannot login",
            email_from="grace@company.com",
            is_login_issue=True,
        )

        decision1 = service.decide(employee, ticket)
        decision2 = service.decide(employee, ticket)

        assert decision1.action == decision2.action
        assert decision1.reason == decision2.reason


class TestDecisionServiceAllActions:
    """Verify all decision actions are used."""

    def test_approve_reactivation_action_exists(self, service):
        """APPROVE_REACTIVATION action should be possible."""
        employee = Employee(
            employee_id="EMP009",
            name="Henry Taylor",
            email="henry@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=10,
            name="Cannot login",
            email_from="henry@company.com",
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.APPROVE_REACTIVATION

    def test_manual_review_action_exists(self, service):
        """MANUAL_REVIEW action should be possible."""
        employee = Employee(
            employee_id="EMP010",
            name="Ivy Martinez",
            email="ivy@company.com",
            status=EmployeeStatus.TERMINATED,
        )

        ticket = Ticket(
            id=11,
            name="Cannot login",
            email_from="ivy@company.com",
            is_login_issue=True,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.MANUAL_REVIEW

    def test_skip_action_exists(self, service):
        """SKIP action should be possible."""
        employee = Employee(
            employee_id="EMP011",
            name="Jack Robinson",
            email="jack@company.com",
            status=EmployeeStatus.ACTIVE,
        )

        ticket = Ticket(
            id=12,
            name="General question",
            email_from="jack@company.com",
            is_login_issue=False,
        )

        decision = service.decide(employee, ticket)

        assert decision.action == Decision.SKIP
