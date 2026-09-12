"""
Configuration for Bronze ingestion: S3 paths and domain registry.

Mirrors the role of generators/config.py, but for ingestion concerns
(where things live in S3) rather than generation concerns (data volume,
dirty-data rates). Kept separate because these are genuinely different
axes of configuration.
"""

from dataclasses import dataclass


@dataclass
class IngestionConfig:
    bucket: str = "fitnesspulse-lakehouse-403322446403"

    @property
    def raw_root(self) -> str:
        return f"s3://{self.bucket}/raw"

    @property
    def bronze_root(self) -> str:
        return f"s3://{self.bucket}/bronze"


# Event domains ingested via the generic bronze_ingest pipeline.
# users/devices are reference data, ingested separately (see run_bronze_ingest.py)
# since they're single files, not date-partitioned event streams.
EVENT_DOMAINS = ["workouts", "heart_rate", "daily_activity", "sleep"]