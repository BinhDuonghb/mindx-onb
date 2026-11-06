"""Mock HR system data for testing."""

from srcs.models import Employee, EmployeeStatus
from datetime import datetime

# Mock employee records - represents what would come from real HR system
MOCK_EMPLOYEES = {
    "duongdznhat98@gmail.com": {
        "employee_id": 101,
        "name": "John Active",
        "email": "duongdznhat98@gmail.com",
        "status": "active",
        "department": "Engineering",
        "manager_email": "manager@company.com",
        "is_internal": True,
        "company_id": 1,
        "lms_account_status": "active",
        "deactivation_reason": None,
    },
    "duonghb1577@gmail.com": {
        "employee_id": 102,
        "name": "Jane Terminated",
        "email": "duonghb1577@gmail.com",
        "status": "terminated",
        "department": "Sales",
        "manager_email": "manager@company.com",
        "is_internal": True,
        "company_id": 1,
        "lms_account_status": "deactivated",
        "deactivation_reason": "Employee terminated",
    },
    "onleave_emp@company.com": {
        "employee_id": 103,
        "name": "Bob OnLeave",
        "email": "onleave_emp@company.com",
        "status": "on_leave",
        "department": "HR",
        "manager_email": "manager@company.com",
        "is_internal": True,
        "company_id": 1,
        "lms_account_status": "suspended",
        "deactivation_reason": "On leave",
    },
    "inactive_emp@company.com": {
        "employee_id": 104,
        "name": "Alice Inactive",
        "email": "inactive_emp@company.com",
        "status": "inactive",
        "department": "Marketing",
        "manager_email": "manager@company.com",
        "is_internal": False,
        "company_id": 1,
        "lms_account_status": "deactivated",
        "deactivation_reason": "Account inactive - 30+ days",
    },
}

# Mock employee by ID
MOCK_EMPLOYEES_BY_ID = {
    101: MOCK_EMPLOYEES["duongdznhat98@gmail.com"],
    102: MOCK_EMPLOYEES["duonghb1577@gmail.com"],
    103: MOCK_EMPLOYEES["onleave_emp@company.com"],
    104: MOCK_EMPLOYEES["inactive_emp@company.com"],
}


def get_mock_employee_by_email(email: str) -> dict:
    """Simulate HR API call to get employee by email.

    Args:
        email: Employee email

    Returns:
        Raw employee data dict from HR system

    Raises:
        KeyError: If employee not found
    """
    if email not in MOCK_EMPLOYEES:
        raise KeyError(f"Employee with email {email} not found in HR system")

    return MOCK_EMPLOYEES[email].copy()


def get_mock_employee_by_id(employee_id: int) -> dict:
    """Simulate HR API call to get employee by ID.

    Args:
        employee_id: Employee ID

    Returns:
        Raw employee data dict from HR system

    Raises:
        KeyError: If employee not found
    """
    if employee_id not in MOCK_EMPLOYEES_BY_ID:
        raise KeyError(f"Employee with ID {employee_id} not found in HR system")

    return MOCK_EMPLOYEES_BY_ID[employee_id].copy()


def create_mock_employee_model(email: str) -> Employee:
    """Create an Employee model from mock data.

    Args:
        email: Employee email

    Returns:
        Employee model instance
    """
    data = get_mock_employee_by_email(email)
    return Employee(
        employee_id=data["employee_id"],
        name=data["name"],
        email=data["email"],
        status=EmployeeStatus(data["status"]),
        department=data["department"],
        manager_email=data["manager_email"],
        is_internal=data["is_internal"],
        company_id=data["company_id"],
        lms_account_status=data["lms_account_status"],
        deactivation_reason=data["deactivation_reason"],
    )
