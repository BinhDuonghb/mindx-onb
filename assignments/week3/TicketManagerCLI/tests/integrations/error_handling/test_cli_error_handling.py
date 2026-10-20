import subprocess
import sys
import pytest
import os


def run_cli_command(command, *args) -> subprocess.CompletedProcess:
    """Helper to run CLI command."""
    cmd = [sys.executable, "main.py", "--test", command] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


class TestCLIErrorHandling:
    """Test CLI error handling for corrupted and missing database files."""

    def test_list_corrupted_json_shows_friendly_error(self, use_temp_test_database):
        """Should show user-friendly error message when JSON is corrupted."""
        # Write corrupted JSON to the temporary test database
        use_temp_test_database.write_text("{ invalid json }", encoding="utf-8")

        result = run_cli_command("list")

        assert result.returncode != 0, "CLI should exit with non-zero code on corrupted JSON"
        assert "corrupted" in result.stdout.lower() or "json" in result.stdout.lower(), \
            f"Should mention corruption. Got: {result.stdout}"
        assert "Traceback" not in result.stdout, "Should not show raw traceback"
        assert "Traceback" not in result.stderr, "Should not show raw traceback in stderr"

    def test_create_corrupted_json_shows_friendly_error(self, use_temp_test_database):
        """Should show user-friendly error when creating with corrupted JSON."""
        # Write corrupted JSON
        use_temp_test_database.write_text("[ invalid", encoding="utf-8")

        result = run_cli_command("create", "--title", "Test Task")

        assert result.returncode != 0, "Should fail when JSON corrupted"
        assert "Traceback" not in result.stdout, "Should not show Python traceback"
        assert "Traceback" not in result.stderr, "Should not show Python traceback"
        assert result.stdout, "Should have error message output"

    def test_delete_corrupted_json_shows_friendly_error(self, use_temp_test_database):
        """Should show user-friendly error when deleting with corrupted JSON."""
        use_temp_test_database.write_text("]]}", encoding="utf-8")

        result = run_cli_command("delete", "550e8400-e29b-41d4-a716-446655440000")

        assert result.returncode != 0, "Should fail when JSON corrupted"
        assert "Traceback" not in result.stdout, "Should not show Python traceback"
        assert "Traceback" not in result.stderr, "Should not show Python traceback"
        assert result.stdout, "Should have error message output"

    def test_list_empty_database_shows_no_tickets_message(self, use_temp_test_database):
        """Should display message when no tickets exist."""
        # File starts empty from fixture
        result = run_cli_command("list")

        assert result.returncode == 0, "Should succeed with empty database"
        assert "no tickets" in result.stdout.lower(), \
            f"Should show 'no tickets' message. Got: {result.stdout}"

    def test_create_succeeds_with_empty_database(self, use_temp_test_database):
        """Should create ticket successfully when database is empty."""
        # File starts empty from fixture
        result = run_cli_command("create", "--title", "Test Task")

        assert result.returncode == 0, f"Should succeed. Got: {result.stderr}"
        assert "successfully" in result.stdout.lower(), \
            f"Should show success message. Got: {result.stdout}"

    def test_corrupted_json_does_not_auto_recover(self, use_temp_test_database):
        """Should NOT automatically overwrite corrupted file."""
        corrupted_content = "{ corrupted: json }"
        use_temp_test_database.write_text(corrupted_content, encoding="utf-8")

        run_cli_command("list")

        # File should still contain corrupted content (not auto-fixed)
        content = use_temp_test_database.read_text(encoding="utf-8")
        assert content == corrupted_content, \
            "CLI should not auto-recover corrupted files (destructive!)"

    def test_corrupted_json_error_suggests_fix_or_restore(self, use_temp_test_database):
        """Error messages should guide users to restore corrupted database."""
        use_temp_test_database.write_text("invalid", encoding="utf-8")

        result = run_cli_command("list")

        output = result.stdout.lower()
        assert "corrupted" in output or "invalid" in output, \
            f"Should mention corruption. Got: {result.stdout}"
        assert "restore" in output or "backup" in output or "fix" in output, \
            f"Should suggest how to fix. Got: {result.stdout}"
