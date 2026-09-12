"""
Applies intentional dirty-data scenarios to already-generated event lists.

This module is deliberately domain-agnostic: every function here operates
on a generic list[dict] of events, using only the shared envelope fields
(event_id, event_timestamp, user_id, device_id, schema_version). This means
one implementation of "duplicate some events" or "null out some IDs" works
identically across workouts, heart rate, daily activity, and sleep - rather
than reimplementing each dirty-data scenario four times.

Each function returns a NEW list; none mutate their input in place, so the
corruption pipeline in generate.py can apply these in a clear, ordered,
debuggable sequence.
"""

import copy
import uuid
from datetime import datetime, timedelta

from src.generators.config import GeneratorConfig


def _sample_indices(n: int, rate: float, rng) -> set[int]:
    """Pick a random subset of indices, sized ~rate * n, without replacement."""
    count = round(n * rate)
    if count <= 0 or n == 0:
        return set()
    return set(rng.sample(range(n), min(count, n)))


def inject_null_ids(events: list[dict], config: GeneratorConfig, rng) -> list[dict]:
    """Null out user_id on a small fraction of events (a required-field violation)."""
    events = copy.deepcopy(events)
    for i in _sample_indices(len(events), config.null_id_rate, rng):
        events[i]["user_id"] = None
    return events


def inject_duplicates(events: list[dict], config: GeneratorConfig, rng) -> list[dict]:
    """Duplicate a fraction of events verbatim (same event_id), simulating
    a producer or ingestion retry sending the same event twice."""
    duplicates = []
    for i in _sample_indices(len(events), config.duplicate_event_rate, rng):
        duplicates.append(copy.deepcopy(events[i]))
    return events + duplicates


def inject_invalid_ranges(events: list[dict], field: str, low, high, config: GeneratorConfig, rng) -> list[dict]:
    """Push a field's value outside a plausible range (e.g. bpm=0 or bpm=300)."""
    events = copy.deepcopy(events)
    for i in _sample_indices(len(events), config.invalid_range_rate, rng):
        if field in events[i]:
            events[i][field] = rng.choice([low, high])
    return events


def inject_impossible_durations(events: list[dict], field: str, config: GeneratorConfig, rng) -> list[dict]:
    """Set a duration-like field to an impossible value (negative or absurdly large)."""
    events = copy.deepcopy(events)
    for i in _sample_indices(len(events), config.impossible_duration_rate, rng):
        if field in events[i]:
            events[i][field] = rng.choice([-1 * abs(events[i][field] or 1), 24 * 60 * 60 * 3])
    return events


def inject_future_timestamps(events: list[dict], config: GeneratorConfig, rng) -> list[dict]:
    """Push event_timestamp into the future relative to the generation run."""
    events = copy.deepcopy(events)
    for i in _sample_indices(len(events), config.future_timestamp_rate, rng):
        future = datetime.utcnow() + timedelta(days=rng.randint(1, 30))
        events[i]["event_timestamp"] = future.strftime("%Y-%m-%dT%H:%M:%SZ")
    return events


def inject_unknown_references(events: list[dict], config: GeneratorConfig, rng) -> list[dict]:
    """Replace user_id or device_id with a random UUID that was never generated,
    simulating a referential-integrity violation (unknown user/device)."""
    events = copy.deepcopy(events)
    for i in _sample_indices(len(events), config.unknown_reference_rate, rng):
        field = rng.choice(["user_id", "device_id"])
        if events[i].get(field) is not None:
            events[i][field] = str(uuid.uuid4())
    return events


def inject_late_arrival(events: list[dict], config: GeneratorConfig, rng) -> list[dict]:
    """
    Simulate late-arriving events by adding an ingested_at field that is
    well after event_timestamp. Silver/Bronze ingestion logic can use this
    field to detect and handle late arrival explicitly, rather than us
    silently shifting event_timestamp (which would corrupt the event's
    true meaning rather than just its arrival behavior).
    """
    events = copy.deepcopy(events)
    for event in events:
        event_time = datetime.strptime(event["event_timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        event["ingested_at"] = (event_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for i in _sample_indices(len(events), config.late_arrival_rate, rng):
        event_time = datetime.strptime(events[i]["event_timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        late_ingest = event_time + timedelta(days=rng.randint(2, 10))
        events[i]["ingested_at"] = late_ingest.strftime("%Y-%m-%dT%H:%M:%SZ")
    return events


def apply_schema_evolution(events: list[dict], config: GeneratorConfig, rng) -> list[dict]:
    """
    Simulate a mid-stream schema change: events timestamped after the
    cutover point are bumped to schema_version_after. This models a real
    scenario where a device firmware or app update changes the event
    schema partway through the data's history.
    """
    events = copy.deepcopy(events)
    if not events:
        return events

    timestamps = sorted(e["event_timestamp"] for e in events)
    cutover_idx = int(len(timestamps) * config.schema_evolution_cutover_fraction)
    cutover_ts = timestamps[min(cutover_idx, len(timestamps) - 1)]

    for event in events:
        if event["event_timestamp"] >= cutover_ts:
            event["schema_version"] = config.schema_version_after
    return events


def apply_all_corruptions(
    events: list[dict],
    config: GeneratorConfig,
    rng,
    numeric_field: str | None = None,
    numeric_range: tuple | None = None,
    duration_field: str | None = None,
) -> list[dict]:
    """
    Apply the full corruption pipeline to a domain's event list, in a fixed
    order chosen so each step operates on a stable, unambiguous input:
    duplicates and unknown-reference swaps happen before null/range/duration
    corruption, so we're not nulling a field on an event that was itself
    just duplicated - keeping each corruption's effect independently traceable.
    """
    events = inject_duplicates(events, config, rng)
    events = inject_unknown_references(events, config, rng)
    events = inject_null_ids(events, config, rng)
    if numeric_field and numeric_range:
        events = inject_invalid_ranges(events, numeric_field, *numeric_range, config, rng)
    if duration_field:
        events = inject_impossible_durations(events, duration_field, config, rng)
    events = inject_future_timestamps(events, config, rng)
    events = inject_late_arrival(events, config, rng)
    events = apply_schema_evolution(events, config, rng)
    return events