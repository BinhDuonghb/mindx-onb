"""HR System Client using JSON file storage via DBClient."""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import json
import shutil
from copy import deepcopy

from data.db_client import DBClient
from srcs.models import Employee, EmployeeStatus, DeactivationReason
from srcs.clients.hr.mock_hr_data import MOCK_EMPLOYEES

logger = logging.getLogger(__name__)


class HRClient:
    """Client for HR system integration using JSON file storage via DBClient.

    ⚠️ CURRENT STATE: Mock/Demo Implementation
    This is a simulated HR adapter using JSON file storage for development and testing.
    It is NOT connected to a real HR system (SAP, Workday, ADP, etc.).

    Real HR API Integration Status:
    - Current: Mock employee data from data/hr.json via DBClient
    - Required before production: Real HR API endpoint integration
    - Pending: Credentials and API documentation from HR team
    - Contact: [HR Team] for real API access

    Handles employee status lookups and verification.
    Uses DBClient to read employee data from JSON file.
    Implements caching with TTL to reduce file reads.

    Graceful handling for missing or corrupt database:
    - If file doesn't exist: initialize with mock data and save it
    - If file is corrupt: back it up and raise an error (don't overwrite)
    - If file is valid: load normally
    """

    def __init__(self, file_path: Path, cache_ttl: int = 300):
        """Initialize HR client.

        Args:
            file_path: Path to JSON file containing employee data
            cache_ttl: Cache time-to-live in seconds (default 300s)

        Raises:
            ValueError: If file contains invalid JSON (after backing up corrupt file)
        """
        self.file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[Employee, datetime]] = {}  # email -> (employee, timestamp)

        # Initialize database with graceful handling
        try:
            self._ensure_database()
        except ValueError as e:
            logger.warning(f"Failed to initialize HR database: {str(e)}")

        self.db_client = DBClient(self.file_path)

    def _ensure_database(self) -> None:
        """Ensure database file exists and is valid.

        If file doesn't exist:
        - Initialize with mock employee data
        - Create parent directories as needed
        - Save to file

        If file exists but is corrupt:
        - Back up the corrupt file to .corrupt
        - Raise ValueError

        If file is valid:
        - Do nothing (DBClient will handle it)

        Raises:
            ValueError: If file exists but contains invalid JSON
        """
        if not self.file_path.exists():
            # Initialize with mock data
            logger.info(f"HR database not found at {self.file_path}, initializing with mock data")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert mock data dict to list format for JSON storage
            employees_list = list(MOCK_EMPLOYEES.values())

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(employees_list, f, indent=2, ensure_ascii=False)

            logger.info(f"Initialized HR database at {self.file_path} with {len(employees_list)} mock employees")
        else:
            # Validate existing file
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Ensure it's a list
                if not isinstance(data, list):
                    raise ValueError(f"HR database must contain a JSON array, got {type(data).__name__}")

                logger.debug(f"HR database validated: {len(data)} employees loaded")

            except json.JSONDecodeError as e:
                # File exists but contains invalid JSON - back it up
                backup_file = Path(str(self.file_path) + ".corrupt")
                try:
                    shutil.copy2(self.file_path, backup_file)
                    error_msg = (
                        f"HR database contains invalid JSON: {self.file_path}\n"
                        f"Corrupt file backed up to: {backup_file}\n"
                        f"Error details: {str(e)}"
                    )
                except Exception as backup_error:
                    error_msg = (
                        f"HR database contains invalid JSON: {self.file_path}\n"
                        f"Failed to back up corrupt file: {str(backup_error)}\n"
                        f"Original error: {str(e)}"
                    )

                logger.error(error_msg)
                raise ValueError(error_msg)

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

    def reactivate_lms_account(
        self, employee_id: str, new_status: str
    ) -> bool:
        """Reactivate employee's LMS account status (not HR employment status).

        Updates only the simulated LMS account fields:
        - lms_account_status: "active", "deactivated", "suspended", etc.
        - deactivation_reason: reason for deactivation if applicable

        Does NOT modify the employee's HR employment status (active/terminated/on-leave/inactive).

        Args:
            employee_id: Employee ID
            new_status: New LMS account status (e.g., "active", "reactivated")

        Returns:
            True if successful, False otherwise
        """
        try:
            employees = self.db_client.read()

            # Find and update employee
            updated = False
            for emp_data in employees:
                if emp_data.get("employee_id") == employee_id:
                    emp_data["lms_account_status"] = new_status
                    emp_data["deactivation_reason"] = None
                    updated = True
                    break

            if not updated:
                logger.warning(f"Employee {employee_id} not found for LMS reactivation")
                return False

            # Write all employees back to file (replaces entire dataset)
            self.db_client._write_all(employees)

            # Clear cache for this employee
            for email, (employee, _) in list(self._cache.items()):
                if employee.employee_id == employee_id:
                    del self._cache[email]
                    break

            logger.info(
                f"Reactivated LMS account for employee {employee_id}: {new_status}"
            )
            return True

        except FileNotFoundError:
            logger.error(f"HR file not found: {self.file_path}")
            return False
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in HR file: {self.file_path}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to reactivate LMS account for {employee_id}: {str(e)}"
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

            # Convert deactivation_reason to enum if present
            deactivation_reason = None
            if emp_data.get("deactivation_reason"):
                reason_str = emp_data.get("deactivation_reason")
                if isinstance(reason_str, str):
                    try:
                        deactivation_reason = DeactivationReason(reason_str)
                    except ValueError:
                        logger.warning(f"Unknown deactivation reason: {reason_str}, treating as OTHER")
                        deactivation_reason = DeactivationReason.OTHER
                else:
                    deactivation_reason = reason_str

            employee = Employee(
                employee_id=emp_data.get("employee_id"),
                name=emp_data.get("name", ""),
                email=emp_data.get("email", ""),
                status=status,
                department=emp_data.get("department"),
                manager_email=emp_data.get("manager_email"),
                is_internal=emp_data.get("is_internal", True),
                company_id=emp_data.get("company_id"),
                lms_account_status=emp_data.get("lms_account_status", "unknown"),
                deactivation_reason=deactivation_reason,
            )

            return employee

        except Exception as e:
            logger.error(f"Failed to parse employee data: {str(e)}")
            raise ValueError(f"Invalid employee data: {str(e)}")
