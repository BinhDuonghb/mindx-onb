"""Integration tests for HR Client using conftest fixture."""

import pytest
import json
from pathlib import Path
from srcs.clients.hr_client import HRClient
from srcs.models import Employee, EmployeeStatus
from data.db_client import DBClient


class TestHRClientEmployeeByEmail:
    """Test employee lookup by email."""

    @pytest.fixture(autouse=True)
    def setup(self, use_temp_test_database):
        """Setup test data in the temporary test database."""
        self.test_db_path = use_temp_test_database
        self.db_client = DBClient(self.test_db_path)

        # Populate test database with mock employees
        employees = [
            {
                "employee_id": 101,
                "name": "John Active",
                "email": "active_emp@company.com",
                "status": "active",
                "department": "Engineering",
                "manager_email": "manager@company.com",
                "is_internal": True,
                "company_id": 1,
            },
            {
                "employee_id": 102,
                "name": "Jane Terminated",
                "email": "terminated_emp@company.com",
                "status": "terminated",
                "department": "Sales",
                "manager_email": "manager@company.com",
                "is_internal": True,
                "company_id": 1,
            },
            {
                "employee_id": 103,
                "name": "Bob OnLeave",
                "email": "onleave_emp@company.com",
                "status": "on_leave",
                "department": "HR",
                "manager_email": "manager@company.com",
                "is_internal": True,
                "company_id": 1,
            },
            {
                "employee_id": 104,
                "name": "Alice Inactive",
                "email": "inactive_emp@company.com",
                "status": "inactive",
                "department": "Marketing",
                "manager_email": "manager@company.com",
                "is_internal": False,
                "company_id": 1,
            },
        ]

        # Write all employees to the test database
        with open(self.test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

    def test_get_active_employee_by_email(self):
        """Should retrieve active employee data by email."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_email("active_emp@company.com")

        assert employee is not None
        assert employee.employee_id == 101
        assert employee.name == "John Active"
        assert employee.email == "active_emp@company.com"
        assert employee.status == EmployeeStatus.ACTIVE
        assert employee.is_active() is True
        assert employee.is_terminated() is False

    def test_get_terminated_employee_by_email(self):
        """Should retrieve terminated employee data by email."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_email("terminated_emp@company.com")

        assert employee is not None
        assert employee.employee_id == 102
        assert employee.status == EmployeeStatus.TERMINATED
        assert employee.is_active() is False
        assert employee.is_terminated() is True

    def test_get_onleave_employee_by_email(self):
        """Should retrieve on-leave employee data by email."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_email("onleave_emp@company.com")

        assert employee is not None
        assert employee.status == EmployeeStatus.ON_LEAVE
        assert employee.is_active() is False

    def test_get_inactive_employee_by_email(self):
        """Should retrieve inactive employee data by email."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_email("inactive_emp@company.com")

        assert employee is not None
        assert employee.status == EmployeeStatus.INACTIVE
        assert employee.is_active() is False
        assert employee.is_internal is False

    def test_employee_not_found_by_email(self):
        """Should return None when employee email not found."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_email("nonexistent@company.com")

        assert employee is None

    def test_employee_lookup_caches_result(self):
        """Should cache employee lookups to reduce file reads."""
        client = HRClient(file_path=self.test_db_path, cache_ttl=60)

        # First call - reads from file
        employee1 = client.get_employee_by_email("active_emp@company.com")
        assert employee1 is not None

        # Verify cache contains the employee
        assert "active_emp@company.com" in client._cache

        # Modify the underlying file
        with open(self.test_db_path, "r", encoding="utf-8") as f:
            employees = json.load(f)

        # Change the employee name (simulating data change)
        for emp in employees:
            if emp["email"] == "active_emp@company.com":
                emp["name"] = "John Modified"
                break

        with open(self.test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

        # Second call - should use cache (returns old name)
        employee2 = client.get_employee_by_email("active_emp@company.com")

        # Verify data is from cache (not modified)
        assert employee2.name == "John Active"
        assert employee1.employee_id == employee2.employee_id


class TestHRClientEmployeeByID:
    """Test employee lookup by ID."""

    @pytest.fixture(autouse=True)
    def setup(self, use_temp_test_database):
        """Setup test data in the temporary test database."""
        self.test_db_path = use_temp_test_database
        self.db_client = DBClient(self.test_db_path)

        employees = [
            {
                "employee_id": 101,
                "name": "John Active",
                "email": "active_emp@company.com",
                "status": "active",
                "department": "Engineering",
            },
            {
                "employee_id": 102,
                "name": "Jane Terminated",
                "email": "terminated_emp@company.com",
                "status": "terminated",
                "department": "Sales",
            },
        ]

        with open(self.test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

    def test_get_employee_by_id(self):
        """Should retrieve employee by ID."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_id(101)

        assert employee is not None
        assert employee.employee_id == 101
        assert employee.name == "John Active"

    def test_get_terminated_employee_by_id(self):
        """Should retrieve terminated employee by ID."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_id(102)

        assert employee is not None
        assert employee.employee_id == 102
        assert employee.status == EmployeeStatus.TERMINATED

    def test_employee_not_found_by_id(self):
        """Should return None when employee ID not found."""
        client = HRClient(file_path=self.test_db_path)

        employee = client.get_employee_by_id(999)

        assert employee is None


class TestHRClientStatusCheck:
    """Test employee status checks."""

    @pytest.fixture(autouse=True)
    def setup(self, use_temp_test_database):
        """Setup test data in the temporary test database."""
        self.test_db_path = use_temp_test_database

        employees = [
            {
                "employee_id": 101,
                "name": "John Active",
                "email": "active_emp@company.com",
                "status": "active",
            },
            {
                "employee_id": 102,
                "name": "Jane Terminated",
                "email": "terminated_emp@company.com",
                "status": "terminated",
            },
        ]

        with open(self.test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

    def test_check_active_employee_status(self):
        """Should identify active employees."""
        client = HRClient(file_path=self.test_db_path)

        status = client.check_employee_status("active_emp@company.com")

        assert status == EmployeeStatus.ACTIVE

    def test_check_terminated_employee_status(self):
        """Should identify terminated employees."""
        client = HRClient(file_path=self.test_db_path)

        status = client.check_employee_status("terminated_emp@company.com")

        assert status == EmployeeStatus.TERMINATED

    def test_check_status_returns_none_on_not_found(self):
        """Should return None when employee not found."""
        client = HRClient(file_path=self.test_db_path)

        status = client.check_employee_status("nonexistent@company.com")

        assert status is None


class TestHRClientCacheManagement:
    """Test cache behavior."""

    @pytest.fixture(autouse=True)
    def setup(self, use_temp_test_database):
        """Setup test data in the temporary test database."""
        self.test_db_path = use_temp_test_database

        employees = [
            {
                "employee_id": 101,
                "name": "John Active",
                "email": "active_emp@company.com",
                "status": "active",
            },
            {
                "employee_id": 102,
                "name": "Jane Terminated",
                "email": "terminated_emp@company.com",
                "status": "terminated",
            },
        ]

        with open(self.test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

    def test_clear_cache(self):
        """Should clear the cache."""
        client = HRClient(file_path=self.test_db_path)

        # Populate cache
        client.get_employee_by_email("active_emp@company.com")
        assert len(client._cache) > 0

        # Clear cache
        client.clear_cache()
        assert len(client._cache) == 0

    def test_multiple_employees_different_cache_entries(self):
        """Should maintain separate cache entries for different employees."""
        client = HRClient(file_path=self.test_db_path)

        # Fetch both employees
        emp1 = client.get_employee_by_email("active_emp@company.com")
        emp2 = client.get_employee_by_email("terminated_emp@company.com")

        assert emp1.status == EmployeeStatus.ACTIVE
        assert emp2.status == EmployeeStatus.TERMINATED
        assert len(client._cache) == 2

    def test_cache_ttl_expiration(self):
        """Cache entries should respect TTL."""
        import time

        client = HRClient(file_path=self.test_db_path, cache_ttl=1)

        # First call
        client.get_employee_by_email("active_emp@company.com")
        assert len(client._cache) == 1

        # Wait for cache to expire (1 second TTL + buffer)
        time.sleep(1.1)

        # Modify the underlying file to test cache expiration
        with open(self.test_db_path, "r", encoding="utf-8") as f:
            employees = json.load(f)

        for emp in employees:
            if emp["email"] == "active_emp@company.com":
                emp["name"] = "John Modified"
                break

        with open(self.test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

        # Second call after expiration should read fresh data
        employee = client.get_employee_by_email("active_emp@company.com")

        # Verify cache was refreshed (has modified name)
        assert employee.name == "John Modified"


class TestHRClientErrorHandling:
    """Test error handling and resilience."""

    def test_handles_missing_file(self):
        """Should handle missing HR file gracefully."""
        non_existent_path = Path("/non/existent/path/hr.json")
        client = HRClient(file_path=non_existent_path)

        employee = client.get_employee_by_email("test@company.com")

        assert employee is None

    def test_handles_invalid_json(self, use_temp_test_database):
        """Should handle invalid JSON gracefully."""
        test_db_path = use_temp_test_database

        # Write invalid JSON
        with open(test_db_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        client = HRClient(file_path=test_db_path)

        employee = client.get_employee_by_email("test@company.com")

        assert employee is None

    def test_handles_missing_email_field(self, use_temp_test_database):
        """Should handle employees with missing email field."""
        test_db_path = use_temp_test_database

        employees = [
            {
                "employee_id": 101,
                "name": "John Active",
                "status": "active",
                # Missing email field
            },
        ]

        with open(test_db_path, "w", encoding="utf-8") as f:
            json.dump(employees, f, indent=2, ensure_ascii=False)

        client = HRClient(file_path=test_db_path)

        employee = client.get_employee_by_email("test@company.com")

        assert employee is None
