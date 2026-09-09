"""
Shared helpers used across all event domain generators.

Keeping envelope construction here (rather than duplicated in workouts.py,
heart_rate.py, daily_activity.py, sleep.py) means every event domain shares
identical envelope shape and behavior by construction, not by convention.
"""

import uuid
from datetime import datetime


def iso_timestamp(dt: datetime) -> str:
    """Format a datetime as ISO-8601 UTC, matching event_contracts.md."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_envelope(
    event_type: str,
    event_timestamp: datetime,
    user_id: str,
    device_id: str | None,
    schema_version: str,
) -> dict:
    """Build the common envelope fields shared by every event type."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_timestamp": iso_timestamp(event_timestamp),
        "schema_version": schema_version,
        "user_id": user_id,
        "device_id": device_id,
    }