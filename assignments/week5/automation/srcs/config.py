"""Configuration module for Odoo automation service.

Configuration selection:
- When pytest is running: Uses TEST_ODOO_* configuration (mocked/test systems)
- When python main.py is running: Uses production ODOO_* configuration
- Detection: Checks if pytest is in sys.modules or PYTEST_TEMP_TEST_DB env var is set
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Detect if running under pytest
_IS_PYTEST = "pytest" in sys.modules or bool(os.environ.get("PYTEST_TEMP_TEST_DB"))

# Production Odoo Configuration
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DATABASE = os.getenv("ODOO_DATABASE")
ODOO_RPC_KEY = os.getenv("ODOO_RPC_KEY")

# Test Odoo Configuration (for pytest and E2E tests)
TEST_ODOO_URL = os.getenv("TEST_ODOO_URL")
TEST_ODOO_DATABASE = os.getenv("TEST_ODOO_DATABASE")
TEST_ODOO_RPC_KEY = os.getenv("TEST_ODOO_RPC_KEY")

# Select active configuration based on execution context
if _IS_PYTEST:
    # Use TEST config when running pytest
    ACTIVE_ODOO_URL = TEST_ODOO_URL
    ACTIVE_ODOO_DATABASE = TEST_ODOO_DATABASE
    ACTIVE_ODOO_RPC_KEY = TEST_ODOO_RPC_KEY
    RUNNING_MODE = "pytest"
else:
    # Use production config when running main.py
    ACTIVE_ODOO_URL = ODOO_URL
    ACTIVE_ODOO_DATABASE = ODOO_DATABASE
    ACTIVE_ODOO_RPC_KEY = ODOO_RPC_KEY
    RUNNING_MODE = "production"

# Validate required configuration
if not all([ACTIVE_ODOO_URL, ACTIVE_ODOO_DATABASE, ACTIVE_ODOO_RPC_KEY]):
    raise ValueError(
        f"Missing required Odoo configuration for {RUNNING_MODE} mode. "
        f"Ensure {'TEST_ODOO_URL, TEST_ODOO_DATABASE, TEST_ODOO_RPC_KEY' if _IS_PYTEST else 'ODOO_URL, ODOO_DATABASE, ODOO_RPC_KEY'} "
        f"are set in .env"
    )

# HR File Configuration
HR_FILE = DATA_DIR / "hr.json"
_temp_test_db = os.environ.get("PYTEST_TEMP_TEST_DB")
TEST_HR_FILE = Path(_temp_test_db) if _temp_test_db else DATA_DIR / "test_hr.json"

def ensure_storage():
    """Ensure data directories and files exist."""
    DATA_DIR.mkdir(exist_ok=True)

    if not HR_FILE.exists():
        HR_FILE.write_text(
            "[]",
            encoding="utf-8"
        )

    if not TEST_HR_FILE.exists():
        TEST_HR_FILE.write_text(
            "[]",
            encoding="utf-8"
        )

# Derived configuration
ODOO_API_ENDPOINT = f"{ACTIVE_ODOO_URL}/json/2"
ODOO_HEADERS = {
    "Authorization": f"Bearer {ACTIVE_ODOO_RPC_KEY}",
    "Content-Type": "application/json",
}

# Service Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Timeouts and Retries
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# HR System Cache TTL (seconds)
HR_CACHE_TTL = int(os.getenv("HR_CACHE_TTL", "300"))

# Odoo Stage Mapping (P2 Issue #4: Remove hardcoded stage IDs)
# Maps workflow outcomes to Odoo stage IDs for ticket updates
# These must be configured by the Odoo administrator based on their system setup
# Configure terminal/Done stage IDs for your own Odoo database, e.g. "7,8".
# Unknown stage meanings must be reviewed by an administrator before enabling automation.
ODOO_STAGE_DONE_IDS = frozenset(
    int(value.strip())
    for value in os.getenv("ODOO_STAGE_DONE_IDS", "").split(",")
    if value.strip()
)

ODOO_STAGE_MAPPING = {
    # Stage ID used when awaiting confirmation from the ticket owner
    # Typically applied after account reactivation is completed
    "awaiting_confirmation": int(os.getenv("ODOO_STAGE_AWAITING_CONFIRMATION", "0")),
}

# Validate stage mapping is configured
if ODOO_STAGE_MAPPING["awaiting_confirmation"] == 0:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "Odoo stage mapping not configured. "
        "Set ODOO_STAGE_AWAITING_CONFIRMATION in .env to the ID of your 'Awaiting Confirmation' stage. "
        "Reactivation workflow will fail safely rather than using a guessed stage ID."
    )

# Gmail SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

# Validate Gmail configuration if required
if not all([SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL]):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "Gmail SMTP configuration incomplete. "
        "Email service will not be available. "
        "Set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL in .env"
    )

__all__ = [
    # Production Odoo Config
    "ODOO_URL",
    "ODOO_DATABASE",
    "ODOO_RPC_KEY",
    # Test Odoo Config
    "TEST_ODOO_URL",
    "TEST_ODOO_DATABASE",
    "TEST_ODOO_RPC_KEY",
    # Active Config (selected based on running context)
    "ACTIVE_ODOO_URL",
    "ACTIVE_ODOO_DATABASE",
    "ACTIVE_ODOO_RPC_KEY",
    "RUNNING_MODE",  # "pytest" or "production"
    "ODOO_API_ENDPOINT",
    "ODOO_HEADERS",
    # HR Configuration
    "HR_FILE",
    "TEST_HR_FILE",
    # Service Configuration
    "LOG_LEVEL",
    "ENVIRONMENT",
    "REQUEST_TIMEOUT",
    "MAX_RETRIES",
    "HR_CACHE_TTL",
    # Gmail SMTP Configuration
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
]
