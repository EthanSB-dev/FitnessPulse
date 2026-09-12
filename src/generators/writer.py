"""
Serializes generated events to local JSON files under data/raw/.

This is the only module in the generator package that touches the filesystem.
Every other module (entities, events/*, corruption) works purely in memory and
returns data structures - keeping I/O isolated here means the rest of the
generator is trivially testable without touching disk, and this module can be
swapped later (e.g. to write directly to S3) without changing generation logic.
"""

import json
import os
from collections import defaultdict

from src.generators.config import GeneratorConfig


def write_events(events: list[dict], domain: str, config: GeneratorConfig) -> list[str]:
    """
    Write events to data/raw/<domain>/<date>.json, partitioned by the
    calendar date portion of each event's event_timestamp. This mirrors
    how a real source system would batch-export events by day, and gives
    Bronze ingestion (Milestone 4) a realistic multi-file structure to read.

    Returns the list of file paths written, for logging/verification.
    """
    by_date: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        # event_timestamp is always "YYYY-MM-DDTHH:MM:SSZ" - the date is the first 10 chars.
        event_date = event["event_timestamp"][:10]
        by_date[event_date].append(event)

    domain_dir = os.path.join(config.output_dir, domain)
    os.makedirs(domain_dir, exist_ok=True)

    written_paths = []
    for event_date, day_events in sorted(by_date.items()):
        file_path = os.path.join(domain_dir, f"{event_date}.json")
        with open(file_path, "w") as f:
            for event in day_events:
                f.write(json.dumps(event) + "\n")
        written_paths.append(file_path)

    return written_paths


def write_entities(entities: list, filename: str, config: GeneratorConfig) -> str:
    """
    Write reference/dimension data (users, devices) as a single JSON file,
    since these are small, don't grow per-day, and don't need date partitioning
    the way high-volume event domains do.
    """
    os.makedirs(config.output_dir, exist_ok=True)
    file_path = os.path.join(config.output_dir, filename)
    with open(file_path, "w") as f:
        for entity in entities:
            # entities are dataclass instances (User, Device) - convert via __dict__
            record = entity.__dict__.copy()
            # dates/dataclass fields that aren't natively JSON-serializable get stringified
            for key, value in record.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    record[key] = str(value)
            f.write(json.dumps(record) + "\n")
    return file_path