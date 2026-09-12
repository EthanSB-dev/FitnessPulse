import uuid
from datetime import datetime


def iso_timestamp(dt: datetime) -> str:
    """Format a datetime as ISO-8601 UTC, matching event_contracts.md."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def seeded_uuid(rng) -> str:
    """
    Generate a UUID using the seeded rng, not uuid.uuid4() (which draws from
    OS randomness and is NOT reproducible even with a fixed seed elsewhere).
    This is what makes the entire generator's seed parameter meaningful.
    """
    return str(uuid.UUID(int=rng.getrandbits(128)))


def make_envelope(
    event_type: str,
    event_timestamp: datetime,
    user_id: str,
    device_id: str | None,
    schema_version: str,
    rng,
) -> dict:
    """Build the common envelope fields shared by every event type."""
    return {
        "event_id": seeded_uuid(rng),
        "event_type": event_type,
        "event_timestamp": iso_timestamp(event_timestamp),
        "schema_version": schema_version,
        "user_id": user_id,
        "device_id": device_id,
    }