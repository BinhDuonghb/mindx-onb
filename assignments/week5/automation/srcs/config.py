"""Configuration module for Odoo automation service."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Odoo API Configuration
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DATABASE = os.getenv("ODOO_DATABASE")
ODOO_RPC_KEY = os.getenv("ODOO_RPC_KEY")

# Validate required configuration
if not all([ODOO_URL, ODOO_DATABASE, ODOO_RPC_KEY]):
    raise ValueError(
        "Missing required Odoo configuration. "
        "Ensure ODOO_URL, ODOO_DATABASE, and ODOO_RPC_KEY are set in .env"
    )

# Derived configuration
ODOO_API_ENDPOINT = f"{ODOO_URL}/json/2"
ODOO_HEADERS = {
    "Authorization": f"Bearer {ODOO_RPC_KEY}",
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

__all__ = [
    "ODOO_URL",
    "ODOO_DATABASE",
    "ODOO_RPC_KEY",
    "ODOO_API_ENDPOINT",
    "ODOO_HEADERS",
    "LOG_LEVEL",
    "ENVIRONMENT",
    "REQUEST_TIMEOUT",
    "MAX_RETRIES",
    "HR_CACHE_TTL",
]
