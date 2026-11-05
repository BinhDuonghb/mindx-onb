"""Odoo API client integration layer.

Clients encapsulate API communication with Odoo systems.
"""

from srcs.clients.odoo.base import ODOOClient
from assignments.week5.automation.srcs.clients.odoo.ticket_client import TicketClient

__all__ = [
    "ODOOClient",
    "TicketClient",
]
