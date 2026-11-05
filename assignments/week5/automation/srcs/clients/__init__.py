"""External system integration layer.

Clients encapsulate API communication with external systems:
- HR system (employee status verification)
- Email service (automated responses)
"""

from srcs.clients.hr.hr_client import HRClient
# from srcs.clients.email_client import EmailClient

__all__ = [
    "HRClient",
    # "EmailClient",
]
