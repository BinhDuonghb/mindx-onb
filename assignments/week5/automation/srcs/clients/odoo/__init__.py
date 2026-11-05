"""Odoo API client integration layer.

Clients encapsulate API communication with Odoo systems.
"""

from srcs.clients.odoo.base import ODOOClient
from srcs.clients.odoo.ticket import TicketClient

__all__ = [
    "ODOOClient",
    "TicketClient",
]
