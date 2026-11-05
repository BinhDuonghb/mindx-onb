"""Data models and schemas for Odoo automation service.

This layer defines data contracts between services - no business logic,
just data representation and validation.
"""

from .ticket import Ticket
from .employee import Employee, EmployeeStatus
from .automation_result import AutomationResult, ActionTaken, ResultStatus

__all__ = [
    "Ticket",
    "Employee",
    "EmployeeStatus",
    "AutomationResult",
    "ActionTaken",
    "ResultStatus",
]
