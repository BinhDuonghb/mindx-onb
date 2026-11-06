"""Ticket fingerprinting for change detection.

Generates content hashes to detect when ticket content has changed,
enabling re-evaluation of previously processed tickets.
"""

import hashlib
import json
from typing import Optional

from srcs.models import Ticket


class TicketFingerprinter:
    """Generate and compare ticket content fingerprints.

    A fingerprint is a SHA-256 hash of ticket content normalized for comparison.
    Fingerprints enable detecting content changes without retaining full ticket history.

    Example:
        fingerprinter = TicketFingerprinter()

        # Generate fingerprint on first processing
        fp1 = fingerprinter.generate(ticket)

        # Later, check if content changed
        fp2 = fingerprinter.generate(ticket)
        if fp1 != fp2:
            print("Content changed - re-evaluate")
    """

    @staticmethod
    def generate(ticket: Ticket) -> str:
        """Generate fingerprint for ticket content.

        Includes all content that affects automation decisions:
        - Ticket name/title
        - Description/body
        - Email from (customer identity)
        - Ticket status
        - Category/tags

        Excludes:
        - Ticket ID (immutable)
        - Creation/update timestamps
        - Internal notes (don't affect automation)
        - Ticket stage (not used for automation)

        Args:
            ticket: Ticket to fingerprint

        Returns:
            SHA-256 hash of normalized ticket content (hex string, 64 chars)
        """
        if not ticket:
            raise ValueError("Ticket cannot be None")

        # Normalize content for consistent hashing
        content = TicketFingerprinter._normalize_content({
            "name": ticket.name,
            "description": ticket.description,
            "email_from": ticket.email_from,
            "stage_id": ticket.stage_id,
            "tags": ticket.tags,
        })

        # Generate SHA-256 hash
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def has_changed(ticket: Ticket, previous_fingerprint: str) -> bool:
        """Check if ticket content has changed.

        Args:
            ticket: Current ticket
            previous_fingerprint: Previously stored fingerprint

        Returns:
            True if content changed, False if unchanged
        """
        if not previous_fingerprint:
            return True

        current = TicketFingerprinter.generate(ticket)
        return current != previous_fingerprint

    @staticmethod
    def _normalize_content(data: dict) -> str:
        """Normalize ticket content for consistent hashing.

        Handles:
        - None/empty values: treated as empty strings
        - Whitespace: normalized
        - Case: converted to lowercase for comparison
        - Order: sorted for consistency

        Args:
            data: Dictionary of ticket fields

        Returns:
            Normalized JSON string
        """
        # Remove None values and empty strings
        cleaned = {}
        for key, value in data.items():
            if value is None:
                cleaned[key] = ""
            elif isinstance(value, str):
                # Normalize whitespace and lowercase
                normalized = " ".join(value.strip().lower().split())
                cleaned[key] = normalized
            else:
                cleaned[key] = str(value).lower()

        # Serialize to JSON with sorted keys for consistent ordering
        return json.dumps(cleaned, sort_keys=True, separators=(',', ':'))
