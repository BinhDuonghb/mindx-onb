"""Global test configuration and fixtures."""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def patch_stage_configuration():
    """P2 Issue #4: Auto-patch Odoo stage configuration for all tests.

    Ensures stage mapping is available so workflows can complete successfully
    without needing to configure environment variables in test fixtures.
    """
    with patch('srcs.config.ODOO_STAGE_MAPPING', {"awaiting_confirmation": 5}):
        yield
