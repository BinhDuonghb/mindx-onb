"""Employee data model for HR system integration."""

from dataclasses import dataclass
from typing import Optional, Union
from enum import Enum


class EmployeeStatus(str, Enum):
    """Valid employee status values."""
    ACTIVE = "active"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"
    INACTIVE = "inactive"


@dataclass
class Employee:
    """Represents employee data from HR system.

    This model acts as a contract between HR API and automation services.
    Used to determine if an employee is still active before account actions.
    """

    employee_id: Union[str, int]
    name: str
    email: str
    status: EmployeeStatus
    department: Optional[str] = None
    manager_email: Optional[str] = None

    # Additional HR attributes
    is_internal: bool = True
    company_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate employee data after initialization."""
        # Employee ID can be string (e.g., "EMP001") or integer
        if not self.employee_id:
            raise ValueError("Employee ID cannot be empty")

        if isinstance(self.employee_id, int) and self.employee_id <= 0:
            raise ValueError("Employee ID (integer) must be positive")
        if not self.name or not self.name.strip():
            raise ValueError("Employee name cannot be empty")
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email address: {self.email}")

        # Ensure status is valid
        if isinstance(self.status, str):
            try:
                self.status = EmployeeStatus(self.status)
            except ValueError:
                raise ValueError(
                    f"Invalid status '{self.status}'. "
                    f"Must be one of: {', '.join([s.value for s in EmployeeStatus])}"
                )

    def is_active(self) -> bool:
        """Check if employee is currently active."""
        return self.status == EmployeeStatus.ACTIVE

    def is_terminated(self) -> bool:
        """Check if employee has been terminated."""
        return self.status == EmployeeStatus.TERMINATED

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "status": self.status.value,
            "department": self.department,
            "manager_email": self.manager_email,
            "is_internal": self.is_internal,
            "company_id": self.company_id,
        }
