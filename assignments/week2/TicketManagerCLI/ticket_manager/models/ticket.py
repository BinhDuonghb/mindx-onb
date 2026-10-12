from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class Ticket:
    id: UUID | None
    title: str
    description: str = ""
    status: str = "open"
    priority: str = "medium"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    creator: Optional[str] = None  # Email of who created the task
    assignee: Optional[str] = None  # Email of who will do the task
    estimated_time: Optional[float] = None  # Estimated time in hours