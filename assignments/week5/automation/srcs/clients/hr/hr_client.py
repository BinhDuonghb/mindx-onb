"""HR System Client using JSON file storage via DBClient."""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import json

from data.db_client import DBClient
from srcs.models import Employee, EmployeeStatus

logger = logging.getLogger(__name__)


class HRClient:
    """Client for HR system integration using JSON file storage.

    Handles employee status lookups and verification.
    Uses DBClient to read employee data from JSON file.
    Implements caching with TTL to reduce file reads.
    """

    def __init__(self, file_path: Path, cache_ttl: int = 300):
        """Initialize HR client.

        Args:
            file_path: Path to JSON file containing employee data
            cache_ttl: Cache time-to-live in seconds (default 300s)
        """
        self.file_path = file_path
        self.cache_ttl = cache_ttl
        self.db_client = DBClient(file_path)
        self._cache: Dict[str, tuple[Employee, datetime]] = {}  # email -> (employee, timestamp)

    def get_employee_by_email(self, email: str) -> Optional[Employee]:
        """Get employee information by email.

        Args:
            email: Employee email address

        Returns:
            Employee model or None if not found

        Raises:
            Exception: On file read errors
        """
        # Check cache first
        if email in self._cache:
            employee, timestamp = self._cache[email]
            # Check if cache entry is still valid
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.debug(f"Cache hit for employee: {email}")
                return employee
            else:
                logger.debug(f"Cache expired for employee: {email}")
                del self._cache[email]

        try:
            employees = self.db_client.read()

            # Search for employee by email
            for emp_data in employees:
                if emp_data.get("email") == email:
                    employee = self._parse_employee(emp_data)
                    # Cache the result
                    self._cache[email] = (employee, datetime.now())
                    logger.debug(f"Found employee by email: {email}")
                    return employee

            logger.warning(f"Employee with email {email} not found")
            return None

        except FileNotFoundError:
            logger.error(f"HR file not found: {self.file_path}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in HR file: {self.file_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to get employee by email {email}: {str(e)}")
            return None

    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Get employee information by ID.

        Args:
            employee_id: Employee ID

        Returns:
            Employee model or None if not found

        Raises:
            Exception: On file read errors
        """
        try:
            employees = self.db_client.read()

            # Search for employee by ID
            for emp_data in employees:
                if emp_data.get("employee_id") == employee_id:
                    employee = self._parse_employee(emp_data)
                    logger.debug(f"Found employee by ID: {employee_id}")
                    return employee

            logger.warning(f"Employee with ID {employee_id} not found")
            return None

        except FileNotFoundError:
            logger.error(f"HR file not found: {self.file_path}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in HR file: {self.file_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to get employee by ID {employee_id}: {str(e)}")
            return None

    def check_employee_status(self, email: str) -> Optional[EmployeeStatus]:
        """Check employee status.

        Args:
            email: Employee email address

        Returns:
            EmployeeStatus or None if lookup fails
        """
        try:
            employee = self.get_employee_by_email(email)
            if employee:
                return employee.status
            return None
        except Exception as e:
            logger.error(f"Failed to check employee status for {email}: {str(e)}")
            return None

    def update_employee_status(
        self, employee_id: str, new_status: str
    ) -> bool:
        """Update employee status in HR system.

        Args:
            employee_id: Employee ID
            new_status: New status value (e.g., "active", "reactivated", "terminated")

        Returns:
            True if successful, False otherwise
        """
        try:
            employees = self.db_client.read()

            # Find and update employee
            for emp_data in employees:
                if emp_data.get("employee_id") == employee_id:
                    emp_data["lms_account_status"] = new_status
                    emp_data["deactivation_reason"] = None
                    self.db_client.write(employees)

                    # Clear cache for this employee
                    email = emp_data.get("email")
                    if email in self._cache:
                        del self._cache[email]

                    logger.info(
                        f"Updated employee {employee_id} status to {new_status}"
                    )
                    return True

            logger.warning(f"Employee {employee_id} not found for status update")
            return False

        except FileNotFoundError:
            logger.error(f"HR file not found: {self.file_path}")
            return False
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in HR file: {self.file_path}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to update employee status for {employee_id}: {str(e)}"
            )
            return False

    def clear_cache(self) -> None:
        """Clear the employee cache."""
        self._cache.clear()
        logger.debug("HR client cache cleared")

    def _parse_employee(self, emp_data: Dict[str, Any]) -> Employee:
        """Parse employee data from JSON into Employee model.

        Args:
            emp_data: Raw employee data dictionary

        Returns:
            Employee model instance

        Raises:
            ValueError: If employee data is invalid
        """
        try:
            # Convert status string to enum if needed
            status = emp_data.get("status", "inactive")
            if isinstance(status, str):
                status = EmployeeStatus(status)

            employee = Employee(
                employee_id=emp_data.get("employee_id"),
                name=emp_data.get("name", ""),
                email=emp_data.get("email", ""),
                status=status,
                department=emp_data.get("department"),
                manager_email=emp_data.get("manager_email"),
                is_internal=emp_data.get("is_internal", True),
                company_id=emp_data.get("company_id"),
            )

            return employee

        except Exception as e:
            logger.error(f"Failed to parse employee data: {str(e)}")
            raise ValueError(f"Invalid employee data: {str(e)}")
