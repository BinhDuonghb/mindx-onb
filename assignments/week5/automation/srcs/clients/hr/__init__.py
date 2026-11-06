"""Odoo API client integration layer.

Clients encapsulate API communication with Odoo systems.
"""

from srcs.clients.hr.hr_client import HRClient
from srcs.clients.hr.mock_hr_data import MOCK_EMPLOYEES, MOCK_EMPLOYEES_BY_ID, get_mock_employee_by_email, get_mock_employee_by_id, create_mock_employee_model

__all__ = [
    "HRClient",
    "MOCK_EMPLOYEES",
    "MOCK_EMPLOYEES_BY_ID",
    "get_mock_employee_by_email",
    "get_mock_employee_by_id",
    "create_mock_employee_model",
]
