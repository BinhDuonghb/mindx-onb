"""Ticket data model representing Odoo helpdesk.ticket records."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Ticket:
    """Represents a helpdesk ticket from Odoo.

    This model acts as a data contract between the Odoo API and internal services.
    Fields are derived from helpdesk.ticket model in Odoo 20.
    """

    id: int
    name: str  # Subject/title
    email_from: str  # Customer email
    description: Optional[str] = None
    category_id: Optional[int] = None  # Ticket category
    stage_id: Optional[int] = None  # Current stage (open, in_progress, closed, etc)
    partner_id: Optional[int] = None  # Customer/partner ID
    create_date: Optional[datetime] = None
    write_date: Optional[datetime] = None

    # Classification for automation
    is_login_issue: bool = False
    issue_type: Optional[str] = None  # e.g., "account_locked", "password_reset", "access_denied"

    # Additional context
    tags: list[str] = field(default_factory=list)
    priority: int = 0  # 0=Low, 1=Medium, 2=High, 3=Urgent

    def __post_init__(self) -> None:
        """Validate ticket data after initialization."""
        if not self.id or self.id <= 0:
            raise ValueError("Ticket ID must be positive")
        if not self.name or not self.name.strip():
            raise ValueError("Ticket name (subject) cannot be empty")
        if not self.email_from or "@" not in self.email_from:
            raise ValueError(f"Invalid email address: {self.email_from}")

    def is_open(self) -> bool:
        """Check if ticket is still open (not closed)."""
        # Stage IDs for closed tickets vary by Odoo setup
        # This is a placeholder - actual implementation depends on your Odoo config
        closed_stages = [7, 8]  # Common closed stage IDs
        return self.stage_id not in closed_stages if self.stage_id else True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "email_from": self.email_from,
            "description": self.description,
            "category_id": self.category_id,
            "stage_id": self.stage_id,
            "partner_id": self.partner_id,
            "create_date": self.create_date.isoformat() if self.create_date else None,
            "write_date": self.write_date.isoformat() if self.write_date else None,
            "is_login_issue": self.is_login_issue,
            "issue_type": self.issue_type,
            "tags": self.tags,
            "priority": self.priority,
        }
