"""Global test configuration and fixtures."""

import pytest
from unittest.mock import patch
from srcs.clients.odoo.write_outcome import WriteOutcome, WriteOutcomeStatus


@pytest.fixture(autouse=True)
def patch_stage_configuration():
    """P2 Issue #4: Auto-patch Odoo stage configuration for all tests.

    Ensures stage mapping is available so workflows can complete successfully
    without needing to configure environment variables in test fixtures.
    """
    with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
        yield


# P2 Issue #5: Helper functions for creating WriteOutcome objects in tests
def write_outcome_success():
    """Create a successful WriteOutcome."""
    return WriteOutcome(status=WriteOutcomeStatus.SUCCESS)


def write_outcome_failure(error: str = "Operation failed"):
    """Create a confirmed-failure WriteOutcome (retryable)."""
    return WriteOutcome(
        status=WriteOutcomeStatus.CONFIRMED_FAILURE,
        error=error,
        is_retryable=True
    )


def write_outcome_unknown(error: str = "Unknown outcome"):
    """Create an ambiguous WriteOutcome (not retryable, requires manual review)."""
    return WriteOutcome(
        status=WriteOutcomeStatus.UNKNOWN,
        error=error,
        is_retryable=False
    )

