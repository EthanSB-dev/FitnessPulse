"""
Central configuration for a synthetic data generation run.

Every generator module (entities, events, corruption) reads its parameters
from a single GeneratorConfig instance rather than hardcoding values. This
keeps run parameters traceable to one place, which matters for two reasons:
1. Reproducibility - the same seed + config always produces the same data.
2. Honesty - README/resume claims about data volume and dirty-data rates
   should be derived from this file, not guessed after the fact.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class GeneratorConfig:
    # --- Reproducibility ---
    seed: int = 42

    # --- Scale ---
    num_users: int = 200
    num_devices_per_user_range: tuple[int, int] = (1, 2)  # most users have 1 device, some 2
    start_date: date = date(2026, 1, 1)
    end_date: date = date(2026, 3, 31)  # ~90 days of simulated history

    # --- Per-domain event volume (rough daily averages per active user) ---
    workouts_per_user_per_week: float = 3.0
    heart_rate_samples_per_workout_minute: float = 1.0  # 1 sample/minute during a workout
    daily_activity_records_per_user_per_day: float = 1.0  # one daily rollup record
    sleep_sessions_per_user_per_day: float = 0.9  # not everyone logs sleep every night

    # --- Dirty-data injection rates (fraction of events affected, 0.0-1.0) ---
    # These apply per-domain via corruption.py functions. Keeping them here
    # (not inside corruption.py) means changing "how dirty" the data is
    # doesn't require touching corruption logic itself.
    null_id_rate: float = 0.01
    duplicate_event_rate: float = 0.02
    invalid_range_rate: float = 0.015
    impossible_duration_rate: float = 0.01
    future_timestamp_rate: float = 0.005
    unknown_reference_rate: float = 0.01  # unknown user_id / device_id
    late_arrival_rate: float = 0.03

    # --- Schema evolution ---
    # Fraction of events (by count, applied near the end of the date range)
    # emitted under a newer schema_version to simulate a mid-stream schema change.
    schema_evolution_cutover_fraction: float = 0.85  # last 15% of the date range
    schema_version_before: str = "1.0"
    schema_version_after: str = "1.1"

    # --- Output ---
    output_dir: str = "data/raw"